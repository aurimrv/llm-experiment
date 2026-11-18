#!/usr/bin/env python3
"""Import a Poke-Tool test set into a Proteum session, execute the mutants, and write a report."""

from __future__ import annotations

import argparse
import os
import pty
import re
import select
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROTEUM = ROOT / "tools" / "ProteumIM64" / "bin"
TES_NAME = re.compile(r"^(?:input|tec)(\d+)\.tes$")
IMPORTED = re.compile(r"(\d+) test cases imported from POKE-TOOL files")


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


def run_pty(cmd: list[str], cwd: Path, env: dict[str, str], timeout: float | None = None) -> str:
    """Run a Proteum command on a pseudo-terminal.

    tcase reads the terminal size while it replays a test case. A pipe makes
    that call fail and the import is dropped.
    """
    eprint("+ " + " ".join(cmd))
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        cmd,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=cwd,
        env=env,
        close_fds=True,
    )
    os.close(slave)
    chunks: list[bytes] = []
    deadline = None if timeout is None else time.monotonic() + timeout
    try:
        while True:
            if deadline is not None and time.monotonic() > deadline:
                proc.kill()
                proc.wait()
                raise SystemExit(f"Command timed out: {' '.join(cmd)}")
            ready, _, _ = select.select([master], [], [], 0.2)
            if not ready:
                if proc.poll() is not None:
                    break
                continue
            try:
                data = os.read(master, 4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        while True:
            ready, _, _ = select.select([master], [], [], 0)
            if not ready:
                break
            try:
                data = os.read(master, 4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
    finally:
        os.close(master)
    code = proc.wait()
    if code != 0:
        raise SystemExit(f"Command failed ({code}): {' '.join(cmd)}")
    return b"".join(chunks).decode("utf-8", errors="replace")


def session_names(program_dir: Path, session: str) -> tuple[str, str]:
    """Return the source name and executable name stored in the Proteum session."""
    ptm = program_dir / f"{session}.PTM"
    if not ptm.is_file():
        raise SystemExit(f"Proteum session not found: {ptm}")
    lines = [line.strip() for line in ptm.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.startswith("gcc ") and index >= 2:
            return lines[index - 2], lines[index - 1]
    raise SystemExit(f"{ptm} does not contain the source and executable names.")


def instrumented_program(program_dir: Path, source: str, executable: str) -> str:
    """Pick the instrumented executable Proteum uses to record the test path."""
    candidates = [f"{executable}_instr", f"{executable}_inst", f"__{source}_inst", f"{source}_inst"]
    seen: list[str] = []
    for name in candidates:
        if name in seen:
            continue
        seen.append(name)
        if (program_dir / name).is_file():
            return name
    names = ", ".join(seen)
    raise SystemExit(f"Instrumented program not found in {program_dir}. Expected one of: {names}")


def test_numbers(testset: Path) -> list[int]:
    if not testset.is_dir():
        raise SystemExit(f"Test set directory not found: {testset}")
    numbers = set()
    for path in testset.iterdir():
        match = TES_NAME.match(path.name)
        if match and path.is_file():
            numbers.add(int(match.group(1)))
    if not numbers:
        raise SystemExit(f"No inputN.tes or tecN.tes files in {testset}")
    return sorted(numbers)


def select_range(numbers: list[int], first: int | None, last: int | None, use_all: bool) -> tuple[int, int]:
    present = set(numbers)
    if use_all:
        start, end = numbers[0], numbers[-1]
    else:
        start = 1 if first is None else first
        end = numbers[-1] if last is None else last
    if start < 1 or end < start:
        raise SystemExit("--first and --last must select a range that starts at 1 or later.")
    missing = [number for number in range(start, end + 1) if number not in present]
    if missing:
        listed = ", ".join(str(number) for number in missing)
        raise SystemExit(f"Test set is missing case {listed}.")
    return start, end


def import_count(output: str) -> int:
    found = IMPORTED.search(output)
    if not found:
        raise SystemExit("tcase -poke did not report how many test cases were imported.")
    return int(found.group(1))


def run_testset(
    program_dir: Path,
    session: str,
    testset: Path,
    first: int | None,
    last: int | None,
    use_all: bool,
) -> Path:
    source, executable = session_names(program_dir, session)
    instrumented = instrumented_program(program_dir, source, executable)
    if not (program_dir / executable).is_file():
        raise SystemExit(f"Session executable not found: {program_dir / executable}")

    start, end = select_range(test_numbers(testset), first, last, use_all)
    env = proteum_env()

    eprint(f"Importing test cases {start} through {end} with {instrumented}")
    imported = run_pty(
        [
            "tcase",
            "-poke",
            "-DD",
            str(testset),
            "-D",
            str(program_dir),
            "-DE",
            str(program_dir),
            "-E",
            executable,
            "-EE",
            instrumented,
            "-trace",
            "-f",
            str(start),
            "-t",
            str(end),
            session,
        ],
        program_dir,
        env,
        timeout=max(60, (end - start + 1) * 30),
    )
    count = import_count(imported)
    expected = end - start + 1
    if count != expected:
        raise SystemExit(f"Expected {expected} imported test cases, and Proteum imported {count}.")

    eprint("Executing mutants")
    run_pty(["exemuta", "-exec", "-trace", "-v", ".", session], program_dir, env)

    report_stem = f"{session}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    eprint(f"Writing {report_stem}.lst")
    run_pty(["report", "-tcase", "-L", "447", "-S", report_stem, session], program_dir, env, timeout=60)
    report = program_dir / f"{report_stem}.lst"
    if not report.is_file():
        named = program_dir / report_stem
        if named.is_file():
            report = named
        else:
            raise SystemExit(f"Proteum did not write {report}")
    eprint(f"Report written to {report}")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import Poke-Tool test cases into a Proteum/IM session, execute the mutants, "
            "and write a timestamped test report."
        )
    )
    parser.add_argument("--program", required=True, type=Path, help="program directory that holds the Proteum session")
    parser.add_argument("--session", required=True, help="Proteum test-session name")
    parser.add_argument("--testset", required=True, type=Path, help="directory of inputN.tes and tecN.tes files")
    parser.add_argument("--first", type=int, help="first test case number to import, starting at 1")
    parser.add_argument("--last", type=int, help="inclusive last test case number to import")
    parser.add_argument("--all", action="store_true", help="import every test case in the directory (the default)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.all and (args.first is not None or args.last is not None):
        raise SystemExit("Use either --all or a --first/--last range.")
    use_all = args.all or (args.first is None and args.last is None)
    run_testset(
        args.program.resolve(),
        args.session,
        args.testset.resolve(),
        args.first,
        args.last,
        use_all,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
