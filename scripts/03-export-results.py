#!/usr/bin/env python3
"""Write a CSV summary and a Poke-Tool test set from an equivalence JSONL file."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROTEUM = ROOT / "tools" / "ProteumIM64" / "bin"
MUTANT_LINE = re.compile(r"MUTANT #\s*(\d+)")
OPERATOR_LINE = re.compile(r"Operator:\s*\d+\s*\(([^)]+)\)")

CSV_FIELDS = [
    "mutant_number",
    "operator",
    "status",
    "input",
    "original_output",
    "mutant_output",
    "input_tokens",
    "output_tokens",
    "input_cost",
    "output_cost",
    "time_spent",
]


def proteum_env() -> dict[str, str]:
    proteum = os.environ.get("PROTEUMIMHOME", "").strip()
    home = Path(proteum) if proteum else DEFAULT_PROTEUM
    if not home.is_dir():
        raise SystemExit(f"Proteum directory not found: {home}")
    env = os.environ.copy()
    env["PROTEUMIMHOME"] = str(home)
    env["PATH"] = str(home) + os.pathsep + env.get("PATH", "")
    return env


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"JSONL file not found: {path}")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number} is not a JSON object") from exc
    if not rows:
        raise SystemExit(f"JSONL file is empty: {path}")
    return rows


def load_operators(program_dir: Path, session: str) -> dict[int, str]:
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
    operators: dict[int, str] = {}
    current: int | None = None
    for line in result.stdout.splitlines():
        mutant = MUTANT_LINE.search(line)
        if mutant:
            current = int(mutant.group(1))
            continue
        operator = OPERATOR_LINE.search(line)
        if operator and current is not None:
            operators[current] = operator.group(1)
    if not operators:
        raise SystemExit(f"muta -l did not list any operators for session {session}")
    return operators


def cell(value) -> str:
    if value is None:
        return ""
    return str(value)


def csv_row(record: dict, operators: dict[int, str]) -> dict[str, str]:
    usage = record.get("usage") or {}
    verification = record.get("verification") or {}
    mutant_id = record.get("mutant_id")
    operator = operators.get(mutant_id, "") if isinstance(mutant_id, int) else ""
    return {
        "mutant_number": cell(mutant_id),
        "operator": operator,
        "status": cell(record.get("status")),
        "input": cell(record.get("stdin")),
        "original_output": cell(verification.get("original_stdout")),
        "mutant_output": cell(verification.get("mutant_stdout")),
        "input_tokens": cell(usage.get("input_tokens")),
        "output_tokens": cell(usage.get("output_tokens")),
        "input_cost": cell(usage.get("input_cost_usd")),
        "output_cost": cell(usage.get("output_cost_usd")),
        "time_spent": cell(record.get("api_seconds")),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def keyboard_input(record: dict) -> str:
    return str(record.get("stdin") or "")


def command_input(record: dict) -> str:
    for key in ("parameters", "argv", "command_line"):
        value = record.get(key)
        if value:
            return str(value)
    return ""


def as_line(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped + "\n"


def write_test_set(directory: Path, cases: list[tuple[str, str]]) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("input*.tes"):
        stale.unlink()
    for stale in directory.glob("tec*.tes"):
        stale.unlink()
    for number, (parameters, keyboard) in enumerate(cases, start=1):
        if parameters:
            (directory / f"input{number}.tes").write_text(parameters, encoding="utf-8")
        if keyboard:
            (directory / f"tec{number}.tes").write_text(keyboard, encoding="utf-8")
    return len(cases)


def distinct_inputs(records: list[dict]) -> list[tuple[str, str]]:
    """One case per distinct pair of command-line parameters and keyboard input."""
    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for record in records:
        parameters = as_line(command_input(record))
        keyboard = as_line(keyboard_input(record))
        if not parameters and not keyboard:
            continue
        key = (parameters, keyboard)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def export_results(program_dir: Path, json_path: Path, session: str, test_dir_name: str) -> None:
    records = load_rows(json_path)
    operators = load_operators(program_dir, session)
    table = [csv_row(record, operators) for record in records]
    csv_path = program_dir / "result" / f"{json_path.stem}.csv"
    write_csv(csv_path, table)
    test_dir = program_dir / test_dir_name
    count = write_test_set(test_dir, distinct_inputs(records))
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"{stamp} Wrote {len(table)} rows to {csv_path}")
    print(f"{stamp} Wrote {count} Poke-Tool test cases to {test_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a CSV and a Poke-Tool test set from one equivalence JSONL file. "
            "The CSV is saved in the program's result directory. "
            "Command-line parameters are written to inputN.tes and keyboard input to tecN.tes. Duplicate inputs are kept once."
        )
    )
    parser.add_argument("--program", required=True, type=Path, help="program directory, such as programs/factorial")
    parser.add_argument("--json", required=True, type=Path, help="equivalence JSONL file for that program")
    parser.add_argument("--session", required=True, help="Proteum session name, used to read mutant operators")
    parser.add_argument(
        "--out",
        required=True,
        help="test-set directory name inside the program directory, such as testset",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    program_dir = args.program.resolve()
    if not program_dir.is_dir():
        raise SystemExit(f"Program directory not found: {program_dir}")
    export_results(program_dir, args.json.resolve(), args.session, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
