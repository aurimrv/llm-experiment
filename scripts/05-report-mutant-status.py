#!/usr/bin/env python3
"""Write a CSV of each mutant's current Proteum status, alive or dead."""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROTEUM = ROOT / "tools" / "ProteumIM64" / "bin"
MUTANT_LINE = re.compile(r"MUTANT #\s*(\d+)")
STATUS_LINE = re.compile(r"Status\s+(\S+)")

CSV_FIELDS = ["mutant_number", "status"]


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


def load_status(program_dir: Path, session: str) -> list[tuple[int, str]]:
    result = subprocess.run(
        ["muta", "-l", session],
        cwd=program_dir,
        env=proteum_env(),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(f"muta -l failed for session {session}. {detail}")

    rows: list[tuple[int, str]] = []
    current: int | None = None
    for line in result.stdout.splitlines():
        mutant = MUTANT_LINE.search(line)
        if mutant:
            current = int(mutant.group(1))
            continue
        status = STATUS_LINE.search(line)
        if status and current is not None:
            rows.append((current, status.group(1).lower()))
            current = None
    if not rows:
        raise SystemExit(f"muta -l did not list any mutants for session {session}")
    return rows


def write_csv(path: Path, rows: list[tuple[int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_FIELDS)
        writer.writerows(rows)


def report(program_dir: Path, session: str) -> Path:
    rows = load_status(program_dir, session)
    destination = program_dir / "result" / f"{session}-mutant-status.csv"
    write_csv(destination, rows)
    counts: dict[str, int] = {}
    for _, status in rows:
        counts[status] = counts.get(status, 0) + 1
    summary = ", ".join(f"{name}={counts[name]}" for name in sorted(counts))
    print(f"{datetime.now():%H:%M:%S} Wrote {len(rows)} mutants to {destination} ({summary})")
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read Proteum's current alive or dead status for every mutant and write a CSV."
    )
    parser.add_argument("--program", required=True, type=Path, help="program directory, such as programs/factorial")
    parser.add_argument("--session", required=True, help="Proteum session name")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    program_dir = args.program.resolve()
    if not program_dir.is_dir():
        raise SystemExit(f"Program directory not found: {program_dir}")
    report(program_dir, args.session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
