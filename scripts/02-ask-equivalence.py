#!/usr/bin/env python3
"""Ask an LLM whether each mutant is equivalent, then run the killing test.

The model must answer with one JSON object. When it says the mutant is not
equivalent, stdin is fed to the original program and to the mutant. The test
counts only when the original finishes on its own and the mutant prints
different stdout, dies from a signal, or does not finish. These programs
leave main without a return, so a non-zero status is not a failure.

Provider, model, timeouts, retries, and the pause between calls come from
the project .env file. The command line overrides provider, model, and
temperature.

Examples:
  python scripts/02-ask-equivalence.py --mutants-dir programs/factorial/mutants --session FACTORIAL --last 2
  python scripts/02-ask-equivalence.py --mutants-dir programs/factorial/mutants --session FACTORIAL --all
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROTEUM_HEADER = ROOT / "tools" / "ProteumIM64" / "bin" / "proteum.h"
MUTANT_NAME = re.compile(r"^muta(\d+)_(.+)\.c$")
STDIN_LIMIT = 4096
LONG_WAIT_SECONDS = 120

SYSTEM_PROMPT = (
    "You judge whether a C mutant is equivalent to the original program. "
    "A mutant is equivalent only when every input produces the same stdout "
    "and the same termination as the original. "
    "If it is not equivalent, give one keyboard input on which the original "
    "program reads the input and finishes, and the mutant prints different "
    "stdout, dies from a signal, or does not finish. "
    "main does not return a value in these programs, so ignore the exit status "
    "and judge by the printed output and by whether the program finishes. "
    "Reply with one JSON object and no markdown."
)


class FatalAPIError(Exception):
    """Stop the sweep. The next mutant would fail for the same reason."""


class APIError(Exception):
    """This mutant failed. The sweep can continue."""


@dataclass
class Settings:
    provider: str
    model: str
    temperature: float
    api_timeout: float
    max_retries: int
    backoff: float
    backoff_max: float
    min_interval: float
    exec_timeout: float
    openrouter_key: str
    openrouter_base: str
    openrouter_reasoning: bool
    ollama_base: str
    ollama_think: bool


class Pace:
    """Minimum gap between the end of one HTTP call and the start of the next."""

    def __init__(self, interval: float):
        self.interval = interval
        self.last_end: float | None = None

    def wait(self) -> None:
        if self.interval <= 0 or self.last_end is None:
            return
        remain = self.interval - (time.monotonic() - self.last_end)
        if remain > 0:
            time.sleep(remain)

    def mark(self) -> None:
        self.last_end = time.monotonic()


def eprint(message: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {message}", file=sys.stderr, flush=True)


def report_mutant(index: int, total: int, mutant_id: int, status: str, previous: float) -> float:
    """Print one mutant result with the seconds spent since the previous one."""
    now = time.monotonic()
    eprint(f"+{now - previous:.1f}s [{index}/{total}] mutant {mutant_id} -> {status}")
    return now


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a number, got {raw!r}") from exc


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"{name} must be true or false, got {raw!r}")


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {raw!r}") from exc


def load_settings(args: argparse.Namespace) -> Settings:
    provider = (args.provider or os.environ.get("LLM_PROVIDER") or "openrouter").strip().lower()
    model = (args.model or os.environ.get("LLM_MODEL") or "").strip()
    if args.temperature is None:
        temperature = env_float("LLM_TEMPERATURE", 0.0)
    else:
        temperature = args.temperature
    if provider not in {"openrouter", "ollama"}:
        raise SystemExit("LLM_PROVIDER must be openrouter or ollama")
    if not model:
        raise SystemExit("Set LLM_MODEL in .env or pass --model")
    return Settings(
        provider=provider,
        model=model,
        temperature=temperature,
        api_timeout=env_float("API_TIMEOUT_SECONDS", 120),
        max_retries=env_int("API_MAX_RETRIES", 5),
        backoff=env_float("API_RETRY_BACKOFF_SECONDS", 2),
        backoff_max=env_float("API_RETRY_BACKOFF_MAX_SECONDS", 60),
        min_interval=env_float("API_MIN_INTERVAL_SECONDS", 3.5),
        exec_timeout=env_float("EXEC_TIMEOUT_SECONDS", 2),
        openrouter_key=os.environ.get("OPENROUTER_API_KEY", "").strip(),
        openrouter_base=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
        openrouter_reasoning=env_bool("OPENROUTER_REASONING", False),
        ollama_base=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
        ollama_think=env_bool("OLLAMA_THINK", False),
    )


def header_wait_seconds(headers, now: float | None = None) -> float | None:
    """Seconds requested by Retry-After or X-RateLimit-Reset, if either is present."""
    if headers is None:
        return None
    now = time.time() if now is None else now
    retry_after = headers.get("Retry-After")
    if retry_after:
        text = str(retry_after).strip()
        try:
            return max(0.0, float(text))
        except ValueError:
            try:
                when = parsedate_to_datetime(text)
            except (TypeError, ValueError, IndexError):
                return None
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, (when - datetime.fromtimestamp(now, timezone.utc)).total_seconds())
    reset = headers.get("X-RateLimit-Reset")
    if not reset:
        return None
    try:
        value = float(str(reset).strip())
    except ValueError:
        return None
    if value > 10_000_000_000:
        return max(0.0, value / 1000.0 - now)
    if value > 1_000_000_000:
        return max(0.0, value - now)
    return max(0.0, value)


def error_details(response: requests.Response) -> tuple[str, str]:
    try:
        body = response.json()
    except ValueError:
        text = response.text.strip().replace("\n", " ")
        return text[:500], ""
    err = body.get("error", body)
    if isinstance(err, str):
        return err[:500], ""
    if not isinstance(err, dict):
        return str(err)[:500], ""
    message = str(err.get("message") or err.get("code") or "")
    metadata = err.get("metadata") or {}
    source = ""
    if isinstance(metadata, dict):
        source = str(metadata.get("limit_source") or "")
    return message[:500], source


USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "input_cost_usd",
    "output_cost_usd",
)


def empty_usage() -> dict:
    return {field: None for field in USAGE_FIELDS}


def _number(value, integer: bool):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if integer else number


def add_usage(left: dict, right: dict) -> dict:
    combined = {}
    for field in USAGE_FIELDS:
        first = left.get(field)
        second = right.get(field)
        if first is None and second is None:
            combined[field] = None
        else:
            combined[field] = (first or 0) + (second or 0)
    return combined


def usage_from_body(body: dict, provider: str) -> dict:
    if provider == "ollama":
        return {
            "input_tokens": _number(body.get("prompt_eval_count"), True),
            "output_tokens": _number(body.get("eval_count"), True),
            "cost_usd": 0.0,
            "input_cost_usd": 0.0,
            "output_cost_usd": 0.0,
        }
    usage = body.get("usage") or {}
    details = usage.get("cost_details") or {}
    return {
        "input_tokens": _number(usage.get("prompt_tokens"), True),
        "output_tokens": _number(usage.get("completion_tokens"), True),
        "cost_usd": _number(usage.get("cost"), False),
        "input_cost_usd": _number(details.get("upstream_inference_prompt_cost"), False),
        "output_cost_usd": _number(details.get("upstream_inference_completions_cost"), False),
    }


def message_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text") or part.get("content") or ""))
        return "".join(parts)
    return str(content)


class ChatClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pace = Pace(settings.min_interval)
        self.session = requests.Session()

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        settings = self.settings
        for attempt in range(settings.max_retries + 1):
            self.pace.wait()
            try:
                response = self._post(messages)
            except (requests.Timeout, requests.ConnectionError) as exc:
                self.pace.mark()
                if attempt >= settings.max_retries:
                    raise APIError(f"connection failed: {exc}") from exc
                delay = self._backoff(attempt)
                eprint(f"connection error, retry {attempt + 1}/{settings.max_retries} after {delay:.1f}s")
                time.sleep(delay)
                continue
            self.pace.mark()
            if response.status_code == 200:
                return self._completion(response)
            self._raise_or_wait(response, attempt)
        raise APIError("retries exhausted")

    def _post(self, messages: list[dict]) -> requests.Response:
        settings = self.settings
        if settings.provider == "openrouter":
            url = f"{settings.openrouter_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.openrouter_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.model,
                "temperature": settings.temperature,
                "messages": messages,
            }
            if not settings.openrouter_reasoning:
                payload["reasoning"] = {"enabled": False}
        else:
            url = f"{settings.ollama_base}/api/chat"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": settings.model,
                "stream": False,
                "think": settings.ollama_think,
                "format": "json",
                "messages": messages,
                "options": {"temperature": settings.temperature},
            }
        return self.session.post(url, headers=headers, json=payload, timeout=settings.api_timeout)

    def _completion(self, response: requests.Response) -> tuple[str, dict]:
        try:
            body = response.json()
        except ValueError as exc:
            raise APIError("provider returned a non-JSON body") from exc
        try:
            if self.settings.provider == "openrouter":
                text = message_text(body["choices"][0]["message"]["content"])
            else:
                text = message_text(body["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise APIError(f"provider response has no message: {str(body)[:300]}") from exc
        return text, usage_from_body(body, self.settings.provider)

    def _raise_or_wait(self, response: requests.Response, attempt: int) -> None:
        status = response.status_code
        message, source = error_details(response)
        label = f"HTTP {status}"
        if source:
            label = f"{label} ({source})"
        if message:
            label = f"{label}: {message}"

        if status in {401, 403, 404}:
            raise FatalAPIError(label)
        if status == 402 and source != "openrouter_in_flight_budget":
            raise FatalAPIError(label)
        if status == 400:
            raise APIError(label)

        retryable = status in {408, 429, 500, 502, 503, 504} or (
            status == 402 and source == "openrouter_in_flight_budget"
        )
        if not retryable:
            raise APIError(label)
        if attempt >= self.settings.max_retries:
            if status in {402, 429}:
                raise FatalAPIError(f"{label}; retries exhausted")
            raise APIError(label)

        delay = header_wait_seconds(response.headers)
        if delay is None:
            delay = self._backoff(attempt)
        elif delay > LONG_WAIT_SECONDS:
            raise FatalAPIError(
                f"{label}; server asked for a {delay:.0f}s wait, which is past the retry budget. "
                "Resume the same output file later."
            )
        eprint(f"{label}; retry {attempt + 1}/{self.settings.max_retries} after {delay:.1f}s")
        time.sleep(delay)

    def _backoff(self, attempt: int) -> float:
        delay = self.settings.backoff * (2**attempt)
        return min(delay, self.settings.backoff_max)


def extract_json_object(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in the answer")
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    value = json.loads(text[start : index + 1])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON object: {exc}") from exc
                if not isinstance(value, dict):
                    raise ValueError("JSON value is not an object")
                return value
    raise ValueError("unbalanced JSON object")


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "y"}:
            return True
        if text in {"false", "no", "n"}:
            return False
    raise ValueError("equivalent must be true or false")


def normalize_stdin(value) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) > STDIN_LIMIT:
        raise ValueError("stdin is longer than 4096 characters")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def interpret_answer(payload: dict) -> tuple[bool, str, str]:
    if "equivalent" not in payload:
        raise ValueError("missing equivalent")
    equivalent = as_bool(payload["equivalent"])
    stdin = normalize_stdin(payload.get("stdin", ""))
    rationale = str(payload.get("rationale") or "").strip()
    return equivalent, stdin, rationale


def user_prompt(mutant_id: int, original: str, mutant: str, diff: str) -> str:
    shown_diff = diff.rstrip() if diff.strip() else "(no textual difference)"
    return (
        f"Original program:\n```c\n{original.rstrip()}\n```\n\n"
        f"Mutant {mutant_id}:\n```c\n{mutant.rstrip()}\n```\n\n"
        f"Diff:\n```diff\n{shown_diff}\n```\n\n"
        "The program reads a single integer from the keyboard. "
        "Use a negative integer, zero, or a positive integer, whichever exposes the mutation. "
        "Put that integer and a trailing newline in stdin. Do not include the prompt the program prints. "
        "If equivalent is true, set stdin to an empty string.\n\n"
        "Reply with exactly this JSON object:\n"
        '{"equivalent": false, "stdin": "<one integer>\\n", "rationale": "<one sentence>"}'
    )


def source_diff(original: str, mutant: str, mutant_id: int) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            mutant.splitlines(keepends=True),
            fromfile="original",
            tofile=f"mutant_{mutant_id}",
        )
    )


def load_id_list(path: Path) -> set[int]:
    """Read one mutant number per line. A missing file means none were recorded."""
    if not path.is_file():
        return set()
    ids: set[int] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        try:
            ids.add(int(text))
        except ValueError as exc:
            raise SystemExit(f"{path}:{line_number} is not a mutant number") from exc
    return ids


def discover_mutants(mutants_dir: Path, session: str, first: int, last: int | None) -> list[int]:
    found = []
    if not mutants_dir.is_dir():
        raise SystemExit(f"mutants directory not found: {mutants_dir}")
    for path in mutants_dir.iterdir():
        match = MUTANT_NAME.match(path.name)
        if not match or match.group(2) != session:
            continue
        mutant_id = int(match.group(1))
        if mutant_id < first:
            continue
        if last is not None and mutant_id > last:
            continue
        found.append(mutant_id)
    return sorted(found)


def completed_ids(path: Path) -> set[int]:
    done = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            done.add(int(json.loads(line)["mutant_id"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return done


def clip(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def compile_source(source: Path, binary: Path) -> tuple[int, str]:
    cmd = ["gcc", "-std=gnu89", "-w"]
    if PROTEUM_HEADER.is_file():
        cmd.extend(["-include", str(PROTEUM_HEADER)])
    cmd.extend(["-o", str(binary), str(source)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "gcc was not found on PATH"
    return result.returncode, result.stderr


def run_binary(binary: Path, stdin: str, timeout: float) -> dict:
    proc = subprocess.Popen(
        [str(binary)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(stdin.encode(), timeout=timeout)
        return {
            "exit": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "timeout": False,
        }
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        return {
            "exit": None,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "timeout": True,
        }


def finished_normally(run: dict) -> bool:
    """The process exited by itself. A missing return in main is still success."""
    return (not run["timeout"]) and isinstance(run["exit"], int) and run["exit"] >= 0


def verification_record(original: dict, mutant: dict, killed: bool) -> dict:
    return {
        "original_exit": original["exit"],
        "mutant_exit": mutant["exit"],
        "original_stdout": clip(original["stdout"]),
        "mutant_stdout": clip(mutant["stdout"]),
        "original_stderr": clip(original["stderr"]),
        "mutant_stderr": clip(mutant["stderr"]),
        "original_timeout": original["timeout"],
        "mutant_timeout": mutant["timeout"],
        "killed": killed,
    }


def verify_test(original_src: Path, mutant_src: Path, stdin: str, exec_timeout: float) -> tuple[str, dict | None, str | None]:
    with tempfile.TemporaryDirectory(prefix="equiv-") as tmp:
        tmp_path = Path(tmp)
        original_code, original_err = compile_source(original_src, tmp_path / "original")
        mutant_code, mutant_err = compile_source(mutant_src, tmp_path / "mutant")
        if original_code != 0 or mutant_code != 0:
            detail = f"original ({original_code}):\n{original_err}\nmutant ({mutant_code}):\n{mutant_err}"
            return "compile_error", None, clip(detail.strip())
        original_run = run_binary(tmp_path / "original", stdin, exec_timeout)
        mutant_run = run_binary(tmp_path / "mutant", stdin, exec_timeout)
        if not finished_normally(original_run):
            record = verification_record(original_run, mutant_run, False)
            return "oracle_failure", record, "original program did not finish"
        killed = (not finished_normally(mutant_run)) or mutant_run["stdout"] != original_run["stdout"]
        record = verification_record(original_run, mutant_run, killed)
        if killed:
            return "killed", record, None
        return "invalid_test", record, "original and mutant produced the same stdout and both finished"


def output_path(args: argparse.Namespace, settings: Settings) -> Path:
    if args.out:
        return Path(args.out)
    model_name = settings.model.replace("/", "__").replace(":", "-")
    program_dir = Path(args.mutants_dir).resolve().parent
    return program_dir / "result" / f"{settings.provider}__{model_name}.jsonl"


def ask_one(client: ChatClient, mutant_id: int, original: str, mutant: str) -> tuple[str, bool, dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(mutant_id, original, mutant, source_diff(original, mutant, mutant_id))},
    ]
    raw, usage = client.complete(messages)
    try:
        interpret_answer(extract_json_object(raw))
        return raw, False, usage
    except ValueError:
        repair = (
            "The previous reply was not one JSON object with keys equivalent, stdin, and rationale. "
            "Reply with only that JSON object."
        )
        messages.append({"role": "assistant", "content": raw[:8000]})
        messages.append({"role": "user", "content": repair})
        repaired, repair_usage = client.complete(messages)
        return repaired, True, add_usage(usage, repair_usage)


def row_base(settings: Settings, mutant_id: int, api_seconds: float) -> dict:
    return {
        "mutant_id": mutant_id,
        "provider": settings.provider,
        "model": settings.model,
        "temperature": settings.temperature,
        "api_seconds": round(api_seconds, 3),
    }


def write_row(handle, row: dict) -> None:
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    handle.flush()


def run_sweep(args: argparse.Namespace, settings: Settings) -> int:
    mutants_dir = Path(args.mutants_dir)
    original_path = mutants_dir / f"original_{args.session}.c"
    if not original_path.is_file():
        raise SystemExit(f"original program not found: {original_path}")
    last = None if args.all and args.last is None else args.last
    mutant_ids = discover_mutants(mutants_dir, args.session, args.first, last)
    if not mutant_ids:
        raise SystemExit("no mutant files matched this session and range")
    anomalous_ids = load_id_list(mutants_dir / "anomalous.txt")
    trivial_ids = load_id_list(mutants_dir / "equivalents-trivial.txt")
    skipped_anomalous = sum(mutant_id in anomalous_ids for mutant_id in mutant_ids)
    skipped_trivial = sum(
        mutant_id in trivial_ids and mutant_id not in anomalous_ids for mutant_id in mutant_ids
    )
    mutant_ids = [
        mutant_id
        for mutant_id in mutant_ids
        if mutant_id not in anomalous_ids and mutant_id not in trivial_ids
    ]
    eprint(f"skipped anomalous={skipped_anomalous} equivalent-trivial={skipped_trivial}")
    if not mutant_ids:
        eprint("nothing to ask")
        return 0

    destination = output_path(args, settings)
    destination.parent.mkdir(parents=True, exist_ok=True)
    done = completed_ids(destination)
    pending = [mutant_id for mutant_id in mutant_ids if mutant_id not in done]
    original = original_path.read_text(encoding="utf-8")

    if settings.provider == "ollama":
        think = f"think={str(settings.ollama_think).lower()} "
    else:
        think = f"reasoning={str(settings.openrouter_reasoning).lower()} "
    eprint(
        f"provider={settings.provider} model={settings.model} temperature={settings.temperature} "
        f"{think}"
        f"timeout={settings.api_timeout:g}s retries={settings.max_retries} "
        f"min_interval={settings.min_interval:g}s exec_timeout={settings.exec_timeout:g}s"
    )
    eprint(
        f"mutants={mutant_ids[0]}..{mutant_ids[-1]} selected={len(mutant_ids)} "
        f"pending={len(pending)} already_done={len(mutant_ids) - len(pending)}"
    )
    eprint(f"output={destination}")
    if not pending:
        eprint("nothing to do")
        return 0

    client = ChatClient(settings)
    counts: Counter[str] = Counter()
    previous = time.monotonic()
    with destination.open("a", encoding="utf-8") as handle:
        for index, mutant_id in enumerate(pending, start=1):
            mutant_path = mutants_dir / f"muta{mutant_id}_{args.session}.c"
            mutant = mutant_path.read_text(encoding="utf-8")
            started = time.monotonic()
            try:
                raw, repaired, usage = ask_one(client, mutant_id, original, mutant)
            except FatalAPIError:
                raise
            except APIError as exc:
                api_seconds = time.monotonic() - started
                row = row_base(settings, mutant_id, api_seconds)
                row.update(
                    {
                        "equivalent_claim": None,
                        "stdin": None,
                        "rationale": None,
                        "raw_response": "",
                        "repair_used": False,
                        "usage": empty_usage(),
                        "status": "api_error",
                        "verification": None,
                        "error": str(exc),
                    }
                )
                write_row(handle, row)
                counts["api_error"] += 1
                previous = report_mutant(index, len(pending), mutant_id, "api_error", previous)
                continue

            api_seconds = time.monotonic() - started
            row = row_base(settings, mutant_id, api_seconds)
            row["raw_response"] = raw
            row["repair_used"] = repaired
            row["usage"] = usage
            try:
                equivalent, stdin, rationale = interpret_answer(extract_json_object(raw))
            except ValueError as exc:
                row.update(
                    {
                        "equivalent_claim": None,
                        "stdin": None,
                        "rationale": None,
                        "status": "parse_error",
                        "verification": None,
                        "error": str(exc),
                    }
                )
                write_row(handle, row)
                counts["parse_error"] += 1
                previous = report_mutant(index, len(pending), mutant_id, "parse_error", previous)
                continue

            row["equivalent_claim"] = equivalent
            row["stdin"] = stdin
            row["rationale"] = rationale
            if equivalent:
                row["status"] = "equivalent"
                row["verification"] = None
                row["error"] = None
            elif not stdin.strip():
                row["status"] = "invalid_test"
                row["verification"] = None
                row["error"] = "model claimed a difference and did not provide stdin"
            else:
                status, verification, error = verify_test(
                    original_path, mutant_path, stdin, settings.exec_timeout
                )
                row["status"] = status
                row["verification"] = verification
                row["error"] = error
            write_row(handle, row)
            counts[row["status"]] += 1
            previous = report_mutant(index, len(pending), mutant_id, row["status"], previous)

    eprint("summary: " + ", ".join(f"{name}={counts[name]}" for name in sorted(counts)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Judge mutant equivalence with OpenRouter or Ollama.")
    parser.add_argument("--provider", choices=["openrouter", "ollama"], help="overrides LLM_PROVIDER")
    parser.add_argument("--model", help="overrides LLM_MODEL")
    parser.add_argument("--temperature", type=float, help="overrides LLM_TEMPERATURE")
    parser.add_argument(
        "--mutants-dir",
        required=True,
        help="directory with original_<session>.c and muta<N>_<session>.c",
    )
    parser.add_argument(
        "--session",
        required=True,
        help="Proteum session name used in the mutant filenames",
    )
    parser.add_argument("--first", type=int, default=0)
    parser.add_argument("--last", type=int, help="inclusive last mutant id")
    parser.add_argument("--all", action="store_true", help="select every mutant file for the session")
    parser.add_argument("--out", help="JSONL path; resumed runs skip mutant ids already in this file")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    args = build_parser().parse_args(argv)
    if not args.all and args.last is None:
        raise SystemExit("Pass --last N or --all. A bare run would call the model for every mutant.")
    settings = load_settings(args)
    if settings.provider == "openrouter" and not settings.openrouter_key:
        raise SystemExit("Set OPENROUTER_API_KEY in .env")
    try:
        return run_sweep(args, settings)
    except FatalAPIError as exc:
        eprint(f"stopped: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
