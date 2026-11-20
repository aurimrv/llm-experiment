#!/usr/bin/env python3
"""Compare equivalence judgments and test sets across the factorial models.

Reads scripts/slms.txt, each programs/factorial-<model> directory, and the
hand classification of equivalent mutants. Writes CSV tables, TikZ figures,
and report.tex.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
Z95 = 1.959963984540054

SCORE_RE = re.compile(r"MUTATION SCORE:\s*([0-9.]+)")
COUNT_RE = {
    "total": re.compile(r"TOTAL MUTANTS:\s*(\d+)"),
    "anomalous": re.compile(r"ANOMALOUS MUTANTS:\s*(\d+)"),
    "alive": re.compile(r"ALIVE MUTANTS:\s*(\d+)"),
    "equivalent_proteum": re.compile(r"EQUIVALENT MUTANTS:\s*(\d+)"),
}


def latex_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def parse_models(path: Path) -> list[dict[str, str]]:
    """One model per line: provider, model. A repeated provider column is ignored."""
    models = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        fields = [field.strip() for field in text.split(",") if field.strip()]
        if len(fields) < 2:
            raise SystemExit(f"{path}:{line_number} needs a provider and a model")
        provider = fields[0]
        model = fields[-1]
        models.append({"provider": provider, "model": model, "order": str(len(models) + 1)})
    if not models:
        raise SystemExit(f"No models in {path}")
    return models


def slug(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


def find_program(provider: str, model: str) -> Path:
    names = [
        f"factorial-{slug(model)}",
        f"factorial-{slug(model.split('/')[-1])}",
        f"factorial-{provider}-{slug(model)}",
    ]
    for name in names:
        path = ROOT / "programs" / name
        if path.is_dir():
            return path
    raise SystemExit(f"No program directory for {provider} {model}. Tried: {', '.join(names)}")


def find_csv(program: Path, provider: str, model: str) -> Path:
    result = program / "result"
    stem = f"{provider}__{model.replace('/', '__').replace(':', '-')}"
    direct = result / f"{stem}.csv"
    if direct.is_file():
        return direct
    matches = [
        path
        for path in result.glob("*.csv")
        if path.name != "FACTORIAL-mutant-status.csv" and slug(model.split("/")[-1]) in path.name
    ]
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(f"No equivalence CSV for {model} in {result}")


def latest_report(program: Path) -> Path:
    reports = sorted(program.glob("FACTORIAL_*.lst"))
    if not reports:
        raise SystemExit(f"No FACTORIAL report in {program}")
    return reports[-1]


def parse_report(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    score = SCORE_RE.search(text)
    if not score:
        raise SystemExit(f"No mutation score in {path}")
    values: dict[str, float] = {"mutation_score": float(score.group(1))}
    for key, pattern in COUNT_RE.items():
        found = pattern.search(text)
        if not found:
            raise SystemExit(f"No {key} count in {path}")
        values[key] = int(found.group(1))
    return values


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_hand(path: Path) -> dict[int, str]:
    status = {}
    for row in read_csv_rows(path):
        status[int(row["mutant_number"])] = row["status"].strip().lower()
    if not status:
        raise SystemExit(f"Hand classification is empty: {path}")
    return status


def normalize_input(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def unique_tests(program: Path) -> list[dict[str, str]]:
    testset = program / "testset"
    numbered: dict[int, dict[str, str]] = {}
    if testset.is_dir():
        for path in sorted(testset.glob("*.tes")):
            match = re.fullmatch(r"(input|tec)(\d+)\.tes", path.name)
            if not match:
                continue
            kind, number = match.group(1), int(match.group(2))
            slot = numbered.setdefault(number, {"command": "", "keyboard": ""})
            field = "command" if kind == "input" else "keyboard"
            slot[field] = normalize_input(path.read_text(encoding="utf-8"))
    seen: set[tuple[str, str]] = set()
    unique = []
    for number in sorted(numbered):
        command = numbered[number]["command"]
        keyboard = numbered[number]["keyboard"]
        if not command and not keyboard:
            continue
        key = (command, keyboard)
        if key in seen:
            continue
        seen.add(key)
        unique.append({"test_number": str(number), "command": command, "keyboard": keyboard})
    return unique


def wilson(successes: int, total: int) -> tuple[float, float, float]:
    """Point estimate and 95% Wilson interval. Undefined when total is zero."""
    if total <= 0:
        return (math.nan, math.nan, math.nan)
    proportion = successes / total
    denom = 1 + Z95**2 / total
    center = (proportion + Z95**2 / (2 * total)) / denom
    margin = Z95 * math.sqrt(proportion * (1 - proportion) / total + Z95**2 / (4 * total**2)) / denom
    return proportion, max(0.0, center - margin), min(1.0, center + margin)


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor
        while end + 1 < len(order) and values[order[end + 1]] == values[order[cursor]]:
            end += 1
        average = (cursor + 1 + end + 1) / 2
        for index in order[cursor : end + 1]:
            ranks[index] = average
        cursor = end + 1
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return math.nan
    return num / (den_x * den_y)


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(rankdata(xs), rankdata(ys))


def fmt(value: float, digits: int = 3) -> str:
    if isinstance(value, float) and math.isnan(value):
        return "NA"
    return f"{value:.{digits}f}"


def pct(value: float) -> str:
    if isinstance(value, float) and math.isnan(value):
        return "NA"
    return f"{100 * value:.1f}\\%"


def csv_cell(value) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        return repr(value) if abs(value) < 1e-6 else f"{value:.10g}"
    return str(value)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_cell(row.get(key, "")) for key in fields})


def format_bar_value(value: float) -> str:
    """Print an integer when the bar is a count, otherwise three decimals."""
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return f"{value:.3f}"


def bar_chart(path: Path, ylabel: str, labels: list[str], values: list[float], lows: list[float] | None, highs: list[float] | None, ymax: float | None) -> None:
    """Write a pgfplots bar chart. Optional lows and highs are Wilson bounds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = [
        (index, value)
        for index, value in enumerate(values)
        if not (isinstance(value, float) and math.isnan(value))
    ]
    placed = []
    for index, value in kept:
        plus = 0.0
        if highs is not None and not math.isnan(highs[index]):
            plus = max(0.0, highs[index] - value)
        placed.append((index, value, plus))
    peak = max((value + plus for _index, value, plus in placed), default=1.0)
    if ymax is None:
        axis_ymax = peak * 1.22 if peak else 1.0
    else:
        axis_ymax = max(ymax, peak) * 1.16
    lines = [
        "\\begin{tikzpicture}",
        "\\begin{axis}[",
        "  ybar,",
        "  bar width=7pt,",
        "  bar shift=0pt,",
        "  width=\\textwidth,",
        "  height=8.2cm,",
        f"  ylabel={{{ylabel}}},",
        "  xtick={" + ",".join(str(index) for index, _value, _plus in placed) + "},",
        "  xticklabels={" + ",".join(latex_escape(labels[index]) for index, _value, _plus in placed) + "},",
        "  x tick label style={rotate=90, anchor=east, font=\\scriptsize, inner sep=1pt, yshift=-4pt},",
        "  y tick label style={font=\\scriptsize},",
        "  label style={font=\\small},",
        "  ymin=0,",
        f"  ymax={axis_ymax:.6f},",
        "  enlarge x limits=0.08,",
        "  tick align=outside,",
        "  clip=false,",
        "]",
    ]
    if lows is None:
        body = " ".join(f"({index},{value:.6f})" for index, value, _plus in placed)
        lines.append("\\addplot+[bar shift=0pt] coordinates {" + body + "};")
    else:
        rows = ["x y minus plus"]
        for index, value, plus in placed:
            minus = 0.0 if math.isnan(lows[index]) else max(0.0, value - lows[index])
            rows.append(f"{index} {value:.6f} {minus:.6f} {plus:.6f}")
        lines.extend(
            [
                "\\addplot+[",
                "  bar shift=0pt,",
                "  error bars/.cd,",
                "  y dir=both,",
                "  y explicit,",
                "  error bar style={thin}",
                "] table[x=x,y=y,y error minus=minus,y error plus=plus] {",
                *rows,
                "};",
            ]
        )
    label_rows = ["x y label"]
    for index, value, plus in placed:
        label_rows.append(f"{index} {value + plus:.6f} {{{format_bar_value(value)}}}")
    lines.extend(
        [
            "\\addplot[",
            "  only marks,",
            "  mark=none,",
            "  bar shift=0pt,",
            "  forget plot,",
            "  nodes near coords,",
            "  point meta=explicit symbolic,",
            "  every node near coord/.append style={font=\\tiny, rotate=90, anchor=west, inner sep=1.5pt, yshift=5pt, fill=white, fill opacity=0.9, text opacity=1},",
            "] table[x=x,y=y,meta=label] {",
            *label_rows,
            "};",
            "\\end{axis}",
            "\\end{tikzpicture}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def scatter_chart(path: Path, rows: list[dict]) -> None:
    coords = " ".join(f"({row['unique_tests']},{float(row['mutation_score']):.6f})" for row in rows)
    path.write_text(
        "\n".join(
            [
                "\\begin{tikzpicture}",
                "\\begin{axis}[",
                "  width=0.82\\textwidth,",
                "  height=7.2cm,",
                "  xlabel={Unique test cases},",
                "  ylabel={Mutation score},",
                "  xmin=-0.4,",
                "  ymin=0,",
                "  ymax=1,",
                "  tick align=outside,",
                "  label style={font=\\small},",
                "  tick label style={font=\\scriptsize},",
                "  only marks,",
                "  mark size=1.8pt,",
                "]",
                "\\addplot coordinates {" + coords + "};",
                "\\end{axis}",
                "\\end{tikzpicture}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def table_tex(rows: list[dict]) -> str:
    lines = [
        "\\begin{tabular}{@{}llrrrrrrr@{}}",
        "\\toprule",
        "Provider & Model & Suggestions & Rate & TP & FP & Precision & Score & Tests \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    latex_escape(row["provider"]),
                    latex_escape(row["label"]),
                    str(row["suggestions"]),
                    pct(row["suggestion_rate"]),
                    str(row["true_positive"]),
                    str(row["false_positive"]),
                    pct(row["precision"]),
                    fmt(row["mutation_score"], 3),
                    str(row["unique_tests"]),
                ]
            )
            + " \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    return "\n".join(lines)


def write_report(path: Path, rows: list[dict], hand_equivalent: list[int], judged_hand: list[int], removed_hand: list[int], rho: float) -> None:
    by_score = sorted(rows, key=lambda row: (-row["mutation_score"], row["label"]))
    by_precision = sorted(
        [row for row in rows if not math.isnan(row["precision"])],
        key=lambda row: (-row["precision"], -row["true_positive"], row["label"]),
    )
    by_suggestions = max(rows, key=lambda row: (row["suggestions"], row["label"]))
    fewest = min(rows, key=lambda row: (row["suggestions"], row["label"]))
    best_score = by_score[0]
    ultra = next(row for row in rows if row["label"] == "nemotron-3-ultra-550b-a55b:free")
    most_tests = max(rows, key=lambda row: (row["unique_tests"], row["label"]))
    best_precision = by_precision[0]
    defined = len(by_precision)
    undefined = [row["label"] for row in rows if math.isnan(row["precision"])]

    def model_line(row: dict) -> str:
        return f"{latex_escape(row['label'])} ({latex_escape(row['provider'])})"

    tied = [
        row
        for row in by_precision
        if abs(row["precision"] - best_precision["precision"]) < 1e-12
    ]
    if len(tied) == 1:
        precision_sentence = (
            f"{model_line(best_precision)} has the highest precision, "
            f"{pct(best_precision['precision'])}, from {best_precision['true_positive']} "
            f"correct suggestions out of {best_precision['suggestions']}. "
            f"Its recall on the {len(judged_hand)} judged hand-equivalent mutants is "
            f"{pct(best_precision['recall'])}."
        )
    else:
        names = "; ".join(
            f"{model_line(row)} ({row['true_positive']} of {row['suggestions']}, recall {pct(row['recall'])})"
            for row in tied
        )
        precision_sentence = (
            f"The highest precision is {pct(best_precision['precision'])}, shared by {names}."
        )
    if len(undefined) == 1:
        undefined_sentence = (
            f" Precision is undefined for {latex_escape(undefined[0])} because that model "
            "suggested no equivalent mutant."
        )
    elif undefined:
        names = ", ".join(latex_escape(name) for name in undefined)
        undefined_sentence = (
            f" Precision is undefined for {names} because those models suggested no equivalent mutant."
        )
    else:
        undefined_sentence = ""

    text = rf"""\documentclass[11pt]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{booktabs}}
\usepackage{{pgfplots}}
\usepackage{{siunitx}}
\pgfplotsset{{compat=1.17}}
\usepackage[T1]{{fontenc}}
\usepackage{{lmodern}}

\title{{Equivalence judgments and mutation scores\\for the factorial program}}
\author{{Generated from the collected model runs}}
\date{{\today}}

\begin{{document}}
\sloppy
\maketitle

\section{{Question and data}}

Fourteen models judged the unit mutants of \texttt{{factorial.c}}. Thirteen ran through Ollama and one, \texttt{{nvidia/nemotron-3-ultra-550b-a55b:free}}, ran through OpenRouter. The list is \texttt{{scripts/slms.txt}}. The repeated provider field on the Ministral 8B line is read as provider \texttt{{ollama}} and model \texttt{{ministral-3:8b}}.

Each model has a directory \texttt{{programs/factorial-<model>}}. The equivalence CSV in \texttt{{result/}} supplies the model status of every mutant. The newest \texttt{{FACTORIAL\_*.lst}} report supplies the Proteum mutation score after that model's test set was executed. The files in \texttt{{testset/}} are the test cases exported from the model.

The hand classification marks {len(hand_equivalent)} of 242 mutants equivalent: {", ".join(str(item) for item in hand_equivalent)}. Two of those, {", ".join(str(item) for item in removed_hand)}, were removed by trivial compiler equivalence before a model was asked, so the models could judge {len(judged_hand)} hand-equivalent mutants. Thirty further mutants are anomalous and were also withheld. A suggestion is a mutant whose model status is \texttt{{equivalent}}. Statuses \texttt{{equivalent-trivial}} and \texttt{{anomalous}} are not model suggestions.

The suggestion rate is the number of suggestions divided by the {rows[0]["judged"]} mutants the model was asked to judge. Precision is the number of those suggestions that are in the hand-equivalent set, divided by the number of suggestions. The Wilson 95\% interval is reported for both proportions. Recall, reported alongside precision, is the fraction of the {len(judged_hand)} judged hand-equivalent mutants that the model suggested. The mutation score is the value Proteum printed. It equals the mutants killed by the executed test set divided by the mutants that remain after anomalous and Proteum-equivalent mutants are removed. Unique test cases are distinct keyboard and command-line inputs in \texttt{{testset/}}.

\section{{Equivalence suggestions}}

The models suggested between {fewest["suggestions"]} and {by_suggestions["suggestions"]} equivalent mutants. {model_line(by_suggestions)} suggested the most, {by_suggestions["suggestions"]} ({pct(by_suggestions["suggestion_rate"])} of the mutants it judged). {model_line(fewest)} suggested the fewest, {fewest["suggestions"]}. Figure~\ref{{fig:suggestions}} shows the counts, with the value printed on each bar. The rate and its Wilson interval are in Table~\ref{{tab:summary}} and Figure~\ref{{fig:rate}}.

\begin{{figure}}[ht]
\centering
\input{{figures/suggestion-count.tex}}
\caption{{Equivalent mutants suggested by each model. The number on each bar is the suggestion count.}}
\label{{fig:suggestions}}
\end{{figure}}

\begin{{figure}}[ht]
\centering
\input{{figures/suggestion-rate.tex}}
\caption{{Suggestion rate among the mutants submitted to the model. The number on each bar is the rate. The intervals are 95\% Wilson intervals, and each number sits above its interval.}}
\label{{fig:rate}}
\end{{figure}}

\section{{Precision against the hand classification}}

{precision_sentence}{undefined_sentence}

A high suggestion count is not a high precision. A model that calls every judged mutant equivalent records a suggestion rate of 100\% and a precision equal to the prevalence of hand-equivalent mutants in that judged set. Figure~\ref{{fig:precision}} shows the defined precisions.

\begin{{figure}}[ht]
\centering
\input{{figures/precision.tex}}
\caption{{Precision of equivalent suggestions against the hand classification. The number on each bar is the precision. The intervals are 95\% Wilson intervals. Models with no suggestions are omitted.}}
\label{{fig:precision}}
\end{{figure}}

\section{{Mutation score}}

After each model's test set was executed, Proteum's mutation score ranged from {fmt(min(row["mutation_score"] for row in rows))} to {fmt(best_score["mutation_score"])}. The highest score is {model_line(best_score)}, with {int(best_score["alive"])} mutants still alive. Figure~\ref{{fig:score}} orders the models by that score. The score already excludes the 30 anomalous mutants and the 2 mutants Proteum holds as equivalent, so it is computed from the mutants the test set killed.

\begin{{figure}}[ht]
\centering
\input{{figures/mutation-score.tex}}
\caption{{Proteum mutation score after executing the test set generated by each model. The number on each bar is the score.}}
\label{{fig:score}}
\end{{figure}}

\subsection{{Alive mutants that separate the two highest scores}}

{model_line(best_score)} left 15 mutants alive: 2, 3, 5, 100, 111, 112, 123, 131, 136, 137, 193, 199, 200, 202, and 231. {model_line(ultra)} left those same 15 alive and also left 197 and 203 alive. Both extra mutants are operator \texttt{{u-VDTR}}. They replace an operand with \texttt{{TRAP\_ON\_ZERO}} applied to \texttt{{fat}}: mutant 197 in the multiplication, and mutant 203 in the printed value. The two extra kills are the whole gap between the scores {fmt(best_score["mutation_score"])} and {fmt(ultra["mutation_score"])}.

Ministral's test set killed both. Proteum records the killing input as test case 6, which is test case \#7 in the test-case report. The keyboard input is 42. For that input the factorial overflows a 32-bit \texttt{{int}} and the original program prints 0, so \texttt{{TRAP\_ON\_ZERO}} fires. A test that produces this difference shows that mutants 197 and 203 differ from the original.

An overflowing factorial prints 0 when the factorial contains at least 32 factors of two. Input 12 still fits and prints 479001600. Inputs 13 through 33 overflow and print a nonzero wrapped value, including 1932053504 for 13 and $-2147483648$ for 32 and 33. From 34 upward, including 42, the program prints 0.

The hand file lists 197 and 203 as equivalent, together with the 15 mutants that stayed alive for both models. The precision and recall in this report follow that file. Under it, the OpenRouter model suggested both mutants were equivalent, so both count as true positives. The killing input shows those two hand labels disagree with the execution. Mutants 167 and 212 are also hand-equivalent, and they are absent from both alive sets because Proteum already holds them as the two trivial equivalents. The OpenRouter session was later updated so the 17 mutants above are marked equivalent; the score in Figure~\ref{{fig:score}} is the score from the report written when those 17 were still alive.

\section{{Unique test cases}}

The exported test sets contain between {min(row["unique_tests"] for row in rows)} and {most_tests["unique_tests"]} distinct inputs. {model_line(most_tests)} produced the largest set. Figure~\ref{{fig:tests}} shows the counts, with the value printed on each bar. Across the 14 models, the Spearman rank correlation between the number of unique test cases and the mutation score is {fmt(rho)}. Figure~\ref{{fig:scatter}} plots the two quantities. The association is descriptive: each model contributes one pair, and the test inputs are not a random sample.

\begin{{figure}}[ht]
\centering
\input{{figures/unique-tests.tex}}
\caption{{Distinct test inputs exported for each model. The number on each bar is the count.}}
\label{{fig:tests}}
\end{{figure}}

\begin{{figure}}[ht]
\centering
\input{{figures/score-vs-tests.tex}}
\caption{{Mutation score against the number of unique test cases.}}
\label{{fig:scatter}}
\end{{figure}}

\section{{Summary}}

Table~\ref{{tab:summary}} collects the four quantities. Suggestions and the suggestion rate answer how many equivalent mutants each model detected. True positives, false positives, and precision answer how many of those detections match the hand classification. The mutation score is the Proteum score after the model's test set ran. Tests is the number of unique inputs in that test set.

\begin{{table}}[ht]
\centering
\caption{{Equivalence suggestions, precision, mutation score, and unique tests. Rate and precision are percentages.}}
\label{{tab:summary}}
\scriptsize
\input{{tables/summary.tex}}
\end{{table}}

\appendix
\section{{Reproducing the tables}}

From the repository root:

\begin{{verbatim}}
python3 analysis/factorial-models/analyze_models.py
Rscript analysis/factorial-models/analyze_models.R
cd analysis/factorial-models && pdflatex report.tex
\end{{verbatim}}

The Python script writes the CSV files in \texttt{{data/}}, the TikZ figures in \texttt{{figures/}}, and this report. The R script reads \texttt{{data/model-summary.csv}} and writes the same Spearman correlation.

\end{{document}}
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze factorial model runs.")
    parser.add_argument("--models", type=Path, default=ROOT / "scripts" / "slms.txt")
    parser.add_argument(
        "--hand",
        type=Path,
        default=Path(
            "/home/auri/.cursor/projects/home-auri-Projects-llm-experiment/attachments/"
            "70813124-68d7-4097-b714-92c54ac00be6/FACTORIAL-mutant-status.csv"
        ),
    )
    args = parser.parse_args()
    hand = load_hand(args.hand)
    hand_equivalent = sorted(mutant for mutant, status in hand.items() if status == "equivalent")
    models = parse_models(args.models)

    summary = []
    decisions = []
    tests = []
    for spec in models:
        program = find_program(spec["provider"], spec["model"])
        rows = read_csv_rows(find_csv(program, spec["provider"], spec["model"]))
        report = parse_report(latest_report(program))
        label = spec["model"].split("/")[-1]
        judged_ids = []
        suggestions = []
        for row in rows:
            mutant = int(row["mutant_number"])
            status = row["status"].strip()
            hand_status = hand.get(mutant, "")
            judged = status not in {"anomalous", "equivalent-trivial"}
            suggested = status == "equivalent"
            if judged:
                judged_ids.append(mutant)
            if suggested:
                suggestions.append(mutant)
            decisions.append(
                {
                    "provider": spec["provider"],
                    "model": spec["model"],
                    "mutant_number": mutant,
                    "operator": row.get("operator", ""),
                    "model_status": status,
                    "hand_status": hand_status,
                    "judged": int(judged),
                    "suggested_equivalent": int(suggested),
                    "hand_equivalent": int(hand_status == "equivalent"),
                }
            )
        judged_hand = [mutant for mutant in hand_equivalent if mutant in set(judged_ids)]
        removed_hand = [mutant for mutant in hand_equivalent if mutant not in set(judged_ids)]
        true_positive = len(set(suggestions) & set(hand_equivalent))
        false_positive = len(suggestions) - true_positive
        false_negative = len(set(judged_hand) - set(suggestions))
        rate, rate_low, rate_high = wilson(len(suggestions), len(judged_ids))
        precision, prec_low, prec_high = wilson(true_positive, len(suggestions))
        recall, recall_low, recall_high = wilson(true_positive, len(judged_hand))
        denom = report["total"] - report["anomalous"] - report["equivalent_proteum"]
        killed = denom - report["alive"]
        score_check = killed / denom if denom else math.nan
        case_rows = unique_tests(program)
        for case in case_rows:
            tests.append({"provider": spec["provider"], "model": spec["model"], "label": label, **case})
        summary.append(
            {
                "order": spec["order"],
                "provider": spec["provider"],
                "model": spec["model"],
                "label": label,
                "program": str(program.relative_to(ROOT)),
                "judged": len(judged_ids),
                "suggestions": len(suggestions),
                "suggestion_rate": rate,
                "suggestion_low": rate_low,
                "suggestion_high": rate_high,
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "precision": precision,
                "precision_low": prec_low,
                "precision_high": prec_high,
                "recall": recall,
                "recall_low": recall_low,
                "recall_high": recall_high,
                "mutation_score": report["mutation_score"],
                "score_check": score_check,
                "alive": report["alive"],
                "proteum_equivalent": report["equivalent_proteum"],
                "anomalous": report["anomalous"],
                "total_mutants": report["total"],
                "unique_tests": len(case_rows),
                "judged_hand_equivalents": len(judged_hand),
            }
        )

    judged_hand = sorted(
        mutant
        for mutant in hand_equivalent
        if any(
            item["mutant_number"] == mutant and item["judged"] == 1 and item["model"] == models[0]["model"]
            for item in decisions
        )
    )
    removed_hand = [mutant for mutant in hand_equivalent if mutant not in judged_hand]
    rho = spearman(
        [float(row["unique_tests"]) for row in summary],
        [float(row["mutation_score"]) for row in summary],
    )

    data = OUT / "data"
    figures = OUT / "figures"
    tables = OUT / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    write_csv(
        data / "model-summary.csv",
        summary,
        [
            "order",
            "provider",
            "model",
            "label",
            "program",
            "judged",
            "suggestions",
            "suggestion_rate",
            "suggestion_low",
            "suggestion_high",
            "true_positive",
            "false_positive",
            "false_negative",
            "precision",
            "precision_low",
            "precision_high",
            "recall",
            "recall_low",
            "recall_high",
            "mutation_score",
            "score_check",
            "alive",
            "proteum_equivalent",
            "anomalous",
            "total_mutants",
            "unique_tests",
            "judged_hand_equivalents",
        ],
    )
    write_csv(
        data / "mutant-decisions.csv",
        decisions,
        [
            "provider",
            "model",
            "mutant_number",
            "operator",
            "model_status",
            "hand_status",
            "judged",
            "suggested_equivalent",
            "hand_equivalent",
        ],
    )
    write_csv(
        data / "unique-tests.csv",
        tests,
        ["provider", "model", "label", "test_number", "command", "keyboard"],
    )
    write_csv(
        data / "hand-equivalents.csv",
        [{"mutant_number": mutant, "status": "equivalent", "shown_to_model": int(mutant in judged_hand)} for mutant in hand_equivalent],
        ["mutant_number", "status", "shown_to_model"],
    )
    write_csv(data / "spearman.csv", [{"x": "unique_tests", "y": "mutation_score", "rho": rho, "n": len(summary)}], ["x", "y", "rho", "n"])

    labels = [row["label"] for row in summary]
    bar_chart(figures / "suggestion-count.tex", "Equivalent suggestions", labels, [row["suggestions"] for row in summary], None, None, None)
    bar_chart(
        figures / "suggestion-rate.tex",
        "Suggestion rate",
        labels,
        [row["suggestion_rate"] for row in summary],
        [row["suggestion_low"] for row in summary],
        [row["suggestion_high"] for row in summary],
        1,
    )
    precision_rows = [row for row in summary if not math.isnan(row["precision"])]
    bar_chart(
        figures / "precision.tex",
        "Precision",
        [row["label"] for row in precision_rows],
        [row["precision"] for row in precision_rows],
        [row["precision_low"] for row in precision_rows],
        [row["precision_high"] for row in precision_rows],
        1,
    )
    ordered = sorted(summary, key=lambda row: (-row["mutation_score"], row["label"]))
    bar_chart(
        figures / "mutation-score.tex",
        "Mutation score",
        [row["label"] for row in ordered],
        [row["mutation_score"] for row in ordered],
        None,
        None,
        1,
    )
    bar_chart(
        figures / "unique-tests.tex",
        "Unique test cases",
        labels,
        [row["unique_tests"] for row in summary],
        None,
        None,
        None,
    )
    scatter_chart(figures / "score-vs-tests.tex", summary)
    (tables / "summary.tex").write_text(table_tex(summary), encoding="utf-8")
    write_report(OUT / "report.tex", summary, hand_equivalent, judged_hand, removed_hand, rho)

    mismatches = [
        row["label"]
        for row in summary
        if abs(row["mutation_score"] - row["score_check"]) > 0.0005
    ]
    print(f"Wrote {len(summary)} models to {data}")
    if mismatches:
        print("Score check differed for:", ", ".join(mismatches))
    print(f"Spearman rho (unique tests, mutation score) = {rho:.4f}")


if __name__ == "__main__":
    main()
