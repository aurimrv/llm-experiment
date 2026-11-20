#!/usr/bin/env python3
"""Prepare a C program for the equivalence experiment.

The script compiles the program, creates a Proteum/IM test session, instruments
it, generates every unit mutant, and writes prompt-ready sources into mutants/.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROTEUM = ROOT / "tools" / "ProteumIM64" / "bin"
DEFAULT_DATAFLOW = Path(__file__).resolve().parent / "dataflow-operators-list.txt"
GENERATED = re.compile(r"(\d+)\s+Mutants Generated")
MUTANT_LINE = re.compile(r"MUTANT #\s*(\d+)")
OPERATOR_LINE = re.compile(r"Operator:\s*\d+\s*\(([^)]+)\)")
GCC_ANOMALY = [
    "gcc",
    "-c",
    "-O1",
    "-Wall",
    "-std=gnu89",
    "-Werror=uninitialized",
    "-Werror=maybe-uninitialized",
    "-Wno-implicit-int",
    "-Wno-builtin-declaration-mismatch",
]
CLANG_ANOMALY = [
    "clang",
    "-c",
    "-std=gnu89",
    "-Wuninitialized",
    "-Wconditional-uninitialized",
    "-Werror=uninitialized",
    "-Werror=sometimes-uninitialized",
    "-Werror=conditional-uninitialized",
    "-Wno-incompatible-library-redeclaration",
]
# Papadakis et al.: identical object code at any of these settings is equivalence.
TCE_SETTINGS = (
    ("none", ["-c", "-std=gnu89", "-w"]),
    ("-O", ["-c", "-std=gnu89", "-w", "-O"]),
    ("-O2", ["-c", "-std=gnu89", "-w", "-O2"]),
    ("-O3", ["-c", "-std=gnu89", "-w", "-O3"]),
)


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


def defines_function(line: str, names: set[str]) -> bool:
    """True when the line defines one of the named functions, as in `int main (void)`."""
    return any(re.search(rf"\b{re.escape(name)}\s*\(", line) for name in names)


def strip_preamble(source: str, functions: list[str], label: str) -> str:
    """Keep the source from the first line that defines a named function."""
    names = set(functions)
    lines = source.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if defines_function(line, names):
            return "".join(lines[index:])
    names_text = ", ".join(functions)
    raise SystemExit(f"{label} does not define one of: {names_text}")


def load_dataflow_operators(path: Path) -> set[str]:
    """Read operator acronyms. Blank lines and comments are ignored."""
    if not path.is_file():
        raise SystemExit(f"Data-flow operator list not found: {path}")
    operators = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        acronym = text.split(",")[-1].strip()
        if acronym:
            operators.add(acronym)
    if not operators:
        raise SystemExit(f"Data-flow operator list is empty: {path}")
    return operators


def load_mutant_operators(base_dir: Path, session: str, env: dict[str, str]) -> dict[int, str]:
    listed = run(["muta", "-l", session], base_dir, env)
    operators: dict[int, str] = {}
    current: int | None = None
    for line in listed.stdout.splitlines():
        mutant = MUTANT_LINE.search(line)
        if mutant:
            current = int(mutant.group(1))
            continue
        operator = OPERATOR_LINE.search(line)
        if operator and current is not None:
            operators[current] = operator.group(1)
            current = None
    if not operators:
        raise SystemExit(f"muta -l did not list any mutants for session {session}")
    return operators


def compiler_sees_uninitialized(command: list[str], source: Path, output: Path) -> bool:
    """Compile one mutant and report whether the compiler mentions an uninitialized use."""
    result = subprocess.run(
        [*command, str(source), "-o", str(output)],
        text=True,
        capture_output=True,
    )
    if output.is_file():
        output.unlink()
    return "uninitialized" in (result.stdout + result.stderr).lower()


def anomaly_detector(source: Path) -> str | None:
    """Return gcc, clang, or both when a data-flow mutant reads an undefined variable."""
    detected: list[str] = []
    if compiler_sees_uninitialized(GCC_ANOMALY, source, source.with_suffix(".o")):
        detected.append("gcc")
    clang = shutil.which("clang")
    if clang and compiler_sees_uninitialized(
        [clang, *CLANG_ANOMALY[1:]],
        source,
        source.with_suffix(".o"),
    ):
        detected.append("clang")
    if not detected:
        return None
    return "both" if len(detected) == 2 else detected[0]


def object_codes(source: str, work: Path) -> dict[str, bytes | None]:
    """Compile one source under every TCE setting. The source name stays fixed so it is not part of the object file."""
    src = work / "tce.c"
    obj = work / "tce.o"
    src.write_text(source, encoding="utf-8")
    compiled: dict[str, bytes | None] = {}
    for name, flags in TCE_SETTINGS:
        if obj.is_file():
            obj.unlink()
        result = subprocess.run(
            ["gcc", *flags, str(src), "-o", str(obj)],
            text=True,
            capture_output=True,
        )
        compiled[name] = obj.read_bytes() if result.returncode == 0 and obj.is_file() else None
    return compiled


def trivial_setting(original: dict[str, bytes | None], mutant: dict[str, bytes | None]) -> str | None:
    """Return the first compiler setting whose object code matches the original."""
    for name, _flags in TCE_SETTINGS:
        baseline = original.get(name)
        candidate = mutant.get(name)
        if baseline is not None and candidate == baseline:
            return name
    return None


def mutant_count(output: str) -> int:
    found = GENERATED.findall(output)
    if not found:
        raise SystemExit("muta-gen did not report how many mutants were generated.")
    return int(found[-1])


def prepare(
    base_dir: Path,
    program: str,
    session: str,
    functions: list[str],
    dataflow_operators: set[str],
) -> None:
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
    operators = load_mutant_operators(base_dir, session, env)

    original = base_dir / f"__{program}.c"
    original_text = strip_preamble(original.read_text(encoding="utf-8", errors="replace"), functions, str(original))
    (mutants_dir / f"original_{session}.c").write_text(original_text, encoding="utf-8")

    anomalous: list[int] = []
    trivial: list[int] = []
    kept = 0
    with tempfile.TemporaryDirectory(prefix="tce-") as temporary:
        work = Path(temporary)
        original_code = object_codes(original_text, work)
        if all(code is None for code in original_code.values()):
            raise SystemExit("The original program did not compile for trivial compiler equivalence")
        eprint(f"Checking data-flow mutants and trivial compiler equivalence, writing sources to {mutants_dir}")
        for mutant_id in range(count):
            run(["exemuta", "-build-one", "-x", str(mutant_id), session], base_dir, env)
            wrapped = base_dir / f"muta{mutant_id}_{session}.c"
            if not wrapped.is_file():
                raise SystemExit(f"Proteum did not write {wrapped.name}")
            operator = operators.get(mutant_id, "")
            detector = anomaly_detector(wrapped) if operator in dataflow_operators else None
            if detector:
                run(["muta", "-anomalous", "-x", str(mutant_id), session], base_dir, env)
                anomalous.append(mutant_id)
                eprint(f"  mutant {mutant_id} {operator} anomalous ({detector})")
            else:
                cleaned = strip_preamble(
                    wrapped.read_text(encoding="utf-8", errors="replace"),
                    functions,
                    str(wrapped),
                )
                setting = trivial_setting(original_code, object_codes(cleaned, work))
                if setting:
                    run(["muta", "-equiv", "-x", str(mutant_id), session], base_dir, env)
                    trivial.append(mutant_id)
                    eprint(f"  mutant {mutant_id} {operator} trivially equivalent ({setting})")
                else:
                    (mutants_dir / wrapped.name).write_text(cleaned, encoding="utf-8")
                    kept += 1
            wrapped.unlink()
            binary = base_dir / f"muta{mutant_id}_{session}"
            if binary.is_file():
                binary.unlink()
            if (mutant_id + 1) % 25 == 0 or mutant_id + 1 == count:
                eprint(f"  {mutant_id + 1}/{count}")

    anomaly_list = mutants_dir / "anomalous.txt"
    anomaly_list.write_text("".join(f"{mutant_id}\n" for mutant_id in anomalous), encoding="utf-8")
    trivial_list = mutants_dir / "equivalents-trivial.txt"
    trivial_list.write_text("".join(f"{mutant_id}\n" for mutant_id in trivial), encoding="utf-8")
    eprint(f"Prepared {kept} mutants in {mutants_dir}")
    eprint(f"Wrote {len(anomalous)} anomalous mutant numbers to {anomaly_list}")
    eprint(f"Wrote {len(trivial)} trivially equivalent mutant numbers to {trivial_list}")
    eprint("Updating the mutant database")
    run(["exemuta", "-exec", "-trace", session], base_dir, env)
    write_test_report(base_dir, session, env)


def write_test_report(base_dir: Path, session: str, env: dict[str, str]) -> Path:
    """Write the fullest test-case report this Proteum build can produce."""
    report_stem = f"{session}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    eprint(f"Writing {report_stem}.lst")
    run(["report", "-tcase", "-L", "447", "-S", report_stem, session], base_dir, env)
    report = base_dir / f"{report_stem}.lst"
    if not report.is_file():
        named = base_dir / report_stem
        if named.is_file():
            report = named
        else:
            raise SystemExit(f"Proteum did not write {report}")
    eprint(f"Report written to {report}")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile a C program, create a Proteum/IM session, generate every unit "
            "mutant, save prompt-ready sources in a mutants subdirectory, and write "
            "a timestamped test report."
        )
    )
    parser.add_argument("--base-dir", required=True, type=Path, help="directory that contains <program>.c")
    parser.add_argument("--program", required=True, help="source name without .c")
    parser.add_argument("--session", required=True, help="Proteum test-session name")
    parser.add_argument(
        "--functions",
        required=True,
        type=Path,
        help="text file with one function name per line. The source is kept from that function's definition",
    )
    parser.add_argument(
        "--dataflow-operators",
        type=Path,
        default=DEFAULT_DATAFLOW,
        help="operators that can introduce an undefined variable use. Default: scripts/dataflow-operators-list.txt",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    functions = load_functions(args.functions)
    prepare(
        args.base_dir.resolve(),
        args.program,
        args.session,
        functions,
        load_dataflow_operators(args.dataflow_operators),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
