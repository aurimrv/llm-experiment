#!/usr/bin/env python3
"""Prepare a C program for the equivalence experiment.

The script compiles the program, creates a Proteum/IM test session, instruments
it, generates every unit mutant, and writes prompt-ready sources into mutants/.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROTEUM = ROOT / "tools" / "ProteumIM64" / "bin"
GENERATED = re.compile(r"(\d+)\s+Mutants Generated")


def eprint(message: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {message}", file=sys.stderr, flush=True)


def proteum_env() -> dict[str, str]:
    proteum = os.environ.get("PROTEUMIMHOME", "").strip()
    home = Path(proteum) if proteum else DEFAULT_PROTEUM
    if not home.is_dir():
        raise SystemExit(f"Proteum directory not found: {home}")
    env = os.environ.copy()
    env["PROTEUMIMHOME"] = str(home)
    env["PATH"] = str(home) + os.pathsep + env.get("PATH", "")
    return env


def run(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    eprint("+ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        if result.stderr:
            eprint(result.stderr.rstrip())
        raise SystemExit(f"Command failed ({result.returncode}): {' '.join(cmd)}")
    if result.stderr:
        eprint(result.stderr.rstrip())
    return result


def load_functions(path: Path) -> list[str]:
    """Read one function name per line. Blank lines are ignored."""
    if not path.is_file():
        raise SystemExit(f"Function file not found: {path}")
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if name and not name.startswith("#"):
            names.append(name)
    if not names:
        raise SystemExit(f"Function file is empty: {path}")
    return names


def strip_preamble(source: str, functions: list[str], label: str) -> str:
    """Keep the source from the first line that starts with a named function."""
    names = set(functions)
    lines = source.splitlines(keepends=True)
    for index, line in enumerate(lines):
        fields = line.split()
        if fields and fields[0] in names:
            return "".join(lines[index:])
    names_text = ", ".join(functions)
    raise SystemExit(
        f"{label} does not contain a line whose first word is one of: {names_text}"
    )


def mutant_count(output: str) -> int:
    found = GENERATED.findall(output)
    if not found:
        raise SystemExit("muta-gen did not report how many mutants were generated.")
    return int(found[-1])


def prepare(base_dir: Path, program: str, session: str, functions: list[str]) -> None:
    source = base_dir / f"{program}.c"
    if not source.is_file():
        raise SystemExit(f"Program source not found: {source}")

    env = proteum_env()
    proteum = env["PROTEUMIMHOME"]
    compile_cmd = f"gcc {program}.c -o runner -lm -w -std=gnu89"

    eprint(f"Compiling {source.name}")
    run(["gcc", f"{program}.c", "-o", "runner", "-lm", "-w", "-std=gnu89"], base_dir, env)

    eprint(f"Creating test session {session}")
    run(
        ["test-new", "-S", program, "-E", "runner", "-C", compile_cmd, session],
        base_dir,
        env,
    )

    eprint("Creating the instrumented program")
    run(["instrum", "-EE", session, f"__{program}"], base_dir, env)
    run(
        [
            "gcc",
            f"__{program}_inst.c",
            f"__{program}_pp.c",
            "-o",
            "runner_instr",
            "-lm",
            "-w",
            "-std=gnu89",
            f"-I{proteum}",
        ],
        base_dir,
        env,
    )

    eprint("Generating unit mutants")
    generated = run(["muta-gen", "-r", "-u-", "100", "0", session], base_dir, env)
    count = mutant_count(generated.stdout + generated.stderr)
    eprint(f"{count} unit mutants generated")

    mutants_dir = base_dir / "mutants"
    mutants_dir.mkdir(exist_ok=True)

    original = base_dir / f"__{program}.c"
    original_text = strip_preamble(original.read_text(encoding="utf-8", errors="replace"), functions, str(original))
    (mutants_dir / f"original_{session}.c").write_text(original_text, encoding="utf-8")

    eprint(f"Writing mutant sources to {mutants_dir}")
    for mutant_id in range(count):
        run(["exemuta", "-build-one", "-x", str(mutant_id), session], base_dir, env)
        wrapped = base_dir / f"muta{mutant_id}_{session}.c"
        if not wrapped.is_file():
            raise SystemExit(f"Proteum did not write {wrapped.name}")
        cleaned = strip_preamble(
            wrapped.read_text(encoding="utf-8", errors="replace"),
            functions,
            str(wrapped),
        )
        (mutants_dir / wrapped.name).write_text(cleaned, encoding="utf-8")
        wrapped.unlink()
        binary = base_dir / f"muta{mutant_id}_{session}"
        if binary.is_file():
            binary.unlink()
        if (mutant_id + 1) % 25 == 0 or mutant_id + 1 == count:
            eprint(f"  {mutant_id + 1}/{count}")

    eprint(f"Prepared {count} mutants in {mutants_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile a C program, create a Proteum/IM session, generate every unit "
            "mutant, and save prompt-ready sources in a mutants subdirectory."
        )
    )
    parser.add_argument("--base-dir", required=True, type=Path, help="directory that contains <program>.c")
    parser.add_argument("--program", required=True, help="source name without .c")
    parser.add_argument("--session", required=True, help="Proteum test-session name")
    parser.add_argument(
        "--functions",
        required=True,
        type=Path,
        help="text file with one function name per line. Text before the first of these names is removed",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    functions = load_functions(args.functions)
    prepare(args.base_dir.resolve(), args.program, args.session, functions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
