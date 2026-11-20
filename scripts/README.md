# Scripts

Run every command below from the repository root through `scripts/container.sh`. That starts the `llm-experiment` container, where `gcc`, Python, and Proteum are installed together. Proteum's preprocessor is `proteuIMcpp` inside `tools/ProteumIM64/bin`. The container sets `PROTEUMIMHOME` to that directory. A host `python` command does not, and Proteum then creates a session with no functions.

```bash
cp .env.example .env
```

Set `OPENROUTER_API_KEY` in `.env`. That file is gitignored. The container reads it from the repository mount. The image already has the Python packages from `scripts/requirements.txt`.

Run the experiment scripts in this order. `scripts/container.sh` is how each one is started. It is not a separate step.

1. `01-prepare-program.py` creates the Proteum session and the mutant sources.
2. `02-ask-equivalence.py` asks the model about each mutant and checks the killing test.
3. `03-export-results.py` writes the CSV and the Poke-Tool test set.
4. `04-run-testset.py` imports that test set, executes the mutants, and writes the report.
5. `05-report-mutant-status.py` writes each mutant's current Proteum status, alive or dead.

The examples below use `programs/factorial`. `factorial.c` reads one integer from the keyboard and prints its factorial. `functions.txt` names the function under test, `main`. Step 1 creates the Proteum session `FACTORIAL` in that directory. Run it once, then run steps 2, 3, and 4 against that session. Step 5 reads the status Proteum recorded for each mutant.

## 1. Prepare a program

`01-prepare-program.py` sets up one C program for the experiment. It needs `gcc` and the Proteum commands (`test-new`, `instrum`, `muta-gen`, and `exemuta`). The container sets `PROTEUMIMHOME` to `tools/ProteumIM64/bin`.

The script performs these steps in `--base-dir`:

1. Compile `<program>.c` with `gcc <program>.c -o runner -lm -w -std=gnu89`. `-std=gnu89` accepts older C, including a `main` with no declared return type.
2. Create a Proteum test session named `--session`, with executable `runner`.
3. Instrument the program and compile that version as `runner_instr`.
4. Generate every unit mutant.
5. Mark a data-flow mutant anomalous when `gcc` or `clang` reports that it uses an uninitialized variable. The checked operators are `u-OEAA`, `u-OEBA`, `u-OESA`, `u-SSDL`, and the variable-replacement operators `u-VGAR` through `u-VLTR`, listed in `scripts/dataflow-operators-list.txt`. Their numbers are written to `mutants/anomalous.txt`, one mutant number per line, and their sources are not saved.
6. Compile each remaining mutant and the original program to object code with `gcc -std=gnu89` at no optimization, `-O`, `-O2`, and `-O3`. Both files are compiled under the same source name. A mutant whose object code matches the original at any of those settings is trivially equivalent. Its number is written to `mutants/equivalents-trivial.txt`, one mutant number per line, it is marked equivalent in the session, and its source is not saved.
7. Write the original program and each remaining mutant, without the Proteum preamble, to `<base-dir>/mutants/`.
8. Run `exemuta -exec -trace <session>` so the mutant database includes the anomalous and equivalent mutants, then write a test report with `report -tcase -L 447`. The file is `<session>_YYYYMMDD-HHMMSS.lst` in the program directory. Proteum adds the `.lst` suffix.

`--functions` is a text file with one function name per line. The script keeps each source from the line that defines one of those functions, such as `int main (void)`. For factorial the file is `programs/factorial/functions.txt` and its only name is `main`.

```bash
scripts/container.sh python scripts/01-prepare-program.py \
  --base-dir programs/factorial \
  --program factorial \
  --session FACTORIAL \
  --functions programs/factorial/functions.txt
```

The mutant files are `mutants/original_FACTORIAL.c` and `mutants/muta<N>_FACTORIAL.c`. `mutants/anomalous.txt` and `mutants/equivalents-trivial.txt` list the mutants left out of that set. `02-ask-equivalence.py` skips every mutant number in those files. Create the session once. Running it again in a directory that already has that session fails at `test-new`.

## 2. Ask whether a mutant is equivalent

`02-ask-equivalence.py` sends the original program, one mutant, and their diff to OpenRouter or Ollama. The model must answer with one JSON object:

```json
{"equivalent": false, "stdin": "5\n", "rationale": "one sentence"}
```

If `equivalent` is false, the script compiles both programs and feeds `stdin` to each. The test kills the mutant when the original finishes and the mutant prints different stdout, dies from a signal, or runs longer than `EXEC_TIMEOUT_SECONDS`. The printed output is what is compared.

The container's `gcc` is used. The script compiles with `-std=gnu89` and includes `tools/ProteumIM64/bin/proteum.h`, which supplies `__MAXINT__` and `__MININT__`.

`--mutants-dir` and `--session` are required. The directory must contain `original_<session>.c` and `muta<N>_<session>.c`. Pass `--last` or `--all` as well. A command with neither flag stops before any API call.

Mutant numbers listed in `anomalous.txt` or `equivalents-trivial.txt`, in the same directory, are not sent to the model. Those files hold one mutant number per line. A missing file skips nothing.

```bash
# First three mutants (ids 0, 1, and 2) with the model from .env
scripts/container.sh python scripts/02-ask-equivalence.py \
  --mutants-dir programs/factorial/mutants \
  --session FACTORIAL \
  --last 2

# Every mutant file for the session
scripts/container.sh python scripts/02-ask-equivalence.py \
  --mutants-dir programs/factorial/mutants \
  --session FACTORIAL \
  --all

# Another OpenRouter model
scripts/container.sh python scripts/02-ask-equivalence.py \
  --mutants-dir programs/factorial/mutants \
  --session FACTORIAL \
  --model anthropic/claude-3.5-sonnet \
  --last 2

# Local Ollama model. No API key is required.
scripts/container.sh python scripts/02-ask-equivalence.py \
  --mutants-dir programs/factorial/mutants \
  --session FACTORIAL \
  --provider ollama \
  --model qwen2.5-coder:7b \
  --last 2
```

`--provider`, `--model`, and `--temperature` override `.env`. Other limits stay in `.env`:

| Variable | Role |
|---|---|
| `API_TIMEOUT_SECONDS` | Socket timeout for one chat completion |
| `API_MAX_RETRIES` | Retries for timeouts, connection errors, HTTP 429, and HTTP 5xx |
| `API_RETRY_BACKOFF_SECONDS` | First backoff delay when the server does not say how long to wait |
| `API_RETRY_BACKOFF_MAX_SECONDS` | Cap on that backoff |
| `API_MIN_INTERVAL_SECONDS` | Pause after every completed call. `3.5` stays under 20 requests/minute |
| `EXEC_TIMEOUT_SECONDS` | Time limit for each compiled program |
| `OLLAMA_THINK` | `false` asks Ollama for the JSON answer without a reasoning trace. `true` allows it |
| `OPENROUTER_REASONING` | `false` sends `reasoning.enabled=false`. `true` leaves the model's own default |

A 429 waits for `Retry-After` or `X-RateLimit-Reset` when that wait is under two minutes. A longer wait, an authentication failure, or an out-of-credit response stops the sweep. Start the same command again to continue.

Results go to `<program>/result/<provider>__<model>.jsonl`, beside that program's `mutants` directory. For the factorial program that is `programs/factorial/result/`. `--out` chooses another file. Mutant ids already in the file are skipped, so a stopped run resumes instead of calling the model twice.

Each line includes a `usage` object. `input_tokens` and `output_tokens` are the provider counts. `cost_usd` is the amount OpenRouter charged, in credits. `input_cost_usd` and `output_cost_usd` are the upstream prompt and completion charges when OpenRouter reports that split. A repair call adds its tokens and cost to the first call. Ollama rows use the local token counts and a cost of zero. A failed call stores nulls in `usage`.

Each line has a `status`:

| Status | Meaning |
|---|---|
| `killed` | The stdin finished on the original and exposed the mutant |
| `equivalent` | The model said equivalent. No test was run |
| `invalid_test` | The model said not equivalent, and the stdin did not expose the mutant |
| `oracle_failure` | The original timed out or died from a signal on that stdin |
| `compile_error` | `gcc` rejected the original or the mutant |
| `parse_error` | The answer was still not the JSON object after one repair request |
| `api_error` | The call failed for this mutant and the sweep continued |

## 3. Export a CSV and a test set

`03-export-results.py` reads one JSONL file and the Proteum session. It writes a CSV in the program's `result` directory and a Poke-Tool test set in a subdirectory of the program. `--out testset` creates `programs/factorial/testset`.

Proteum reads two file names. `inputN.tes` holds command-line parameters. `tecN.tes` holds keyboard input. A program that accepts both gets both files with the same number. A program that accepts only one of them gets only that file. The current JSONL stores keyboard input in `stdin`. Command-line parameters are read from `parameters`, `argv`, or `command_line` when a record has one of those fields.

Duplicate inputs are stored once. `0` and `0` followed by a newline are the same keyboard input. A mutant with no input, including one the model called equivalent, does not add a test case. Step 4 imports the directory with `tcase -poke`.

```bash
scripts/container.sh python scripts/03-export-results.py \
  --program programs/factorial \
  --json programs/factorial/result/openrouter__nvidia__nemotron-3-ultra-550b-a55b-free.jsonl \
  --session FACTORIAL \
  --out testset
```

The CSV columns are mutant number, operator, status, input, original output, mutant output, input tokens, output tokens, input cost, output cost, and time spent. The operator comes from `muta -l`. Rows are sorted by mutant number. Mutants listed in `mutants/anomalous.txt` are included with status `anomalous`. Mutants listed in `mutants/equivalents-trivial.txt` are included with status `equivalent-trivial`. A mutant the model judged equivalent keeps the status `equivalent`. The two prepared statuses have empty input, output, token, cost, and time cells.

## 4. Run a test set

`04-run-testset.py` loads a Poke-Tool directory into one Proteum session, executes the mutants, and writes a report. `--program` is the directory that contains the session. `--testset` is the directory of `inputN.tes` and `tecN.tes` files. `--session` is the Proteum session name.

The import records the path taken by each test case. Proteum needs the original executable and the instrumented executable for that. The executable name comes from the session file. The script uses the first instrumented program it finds among `<executable>_instr` (`runner_instr` after step 1), `<executable>_inst`, `__<source>_inst`, and `<source>_inst`.

```bash
tcase -poke -DD <testset> -D <program> -DE <program> -E <executable> -EE <instrumented> -trace -f <first> -t <last> <session>
exemuta -exec -trace -v . <session>
report -tcase -L 447 -S <session>_<timestamp> <session>
```

`-L 447` is the most detailed test-case report this Proteum build can write. It includes the kill counts, whether each case is enabled, the keyboard input, and the program output. Level 511 would also print the execution time, the return code, and the command-line parameters, but that build crashes while printing the parameters.

`tcase` reads the terminal while it replays each test case. The script gives it a pseudo-terminal, so the import also works when standard input is not a terminal.

`--all` is the default and imports every numbered test case in the directory. `--first` and `--last` select an inclusive range. Test case numbers start at 1, matching the file names. `--last 2` imports cases 1 and 2 when `--first` is omitted. Each number in the range must have an `inputN.tes` file, a `tecN.tes` file, or both.

The selected files are added to the test cases already stored in the session. Proteum writes the `-L 447` report in the program directory and adds the `.lst` suffix. The file name is the session name, an underscore, and a `YYYYMMDD-HHMMSS` timestamp, for example `FACTORIAL_20261117-224530.lst`.

```bash
scripts/container.sh python scripts/04-run-testset.py \
  --program programs/factorial \
  --session FACTORIAL \
  --testset programs/factorial/testset
```

A shorter range:

```bash
scripts/container.sh python scripts/04-run-testset.py \
  --program programs/factorial \
  --session FACTORIAL \
  --testset programs/factorial/testset \
  --first 1 \
  --last 1
```

`exemuta` prints one dot per mutant.

## 5. Report alive and dead mutants

`05-report-mutant-status.py` reads the session with `muta -l` and writes `result/<session>-mutant-status.csv` in the program directory. The columns are mutant number and status. Proteum's status word is stored in lowercase, so a killed mutant is `dead` and a mutant the test set did not kill is `alive`.

```bash
scripts/container.sh python scripts/05-report-mutant-status.py \
  --program programs/factorial \
  --session FACTORIAL
```

For factorial that file is `programs/factorial/result/FACTORIAL-mutant-status.csv`.

## Docker

The same tools run in the `llm-experiment` image: Python 3 with `scripts/requirements.txt`, gcc, make, gawk, indent, Tcl/Tk 8.6 (`wish`), xterm, and the ProteumIM programs from `tools/ProteumIM64/bin`. No pyenv is installed. The repository is mounted at `/work`, so `.env` and each program's `result/` directory stay on the host.

The host session is graphical (`DISPLAY` is set, and `/tmp/.X11-unix` exists). The container is a separate machine and only sees that display when the socket and the X authority file are mounted. `scripts/container.sh` does that. ProteumIM itself is `wish` plus the Tcl files; the script `proteumim` in the image opens that interface. The GUI also runs `xterm` when a test case is added from the window, and xterm is in the image.

```bash
# Shell inside the container. Proteum commands are already on PATH.
scripts/container.sh bash

# Same equivalence command as in step 2.
scripts/container.sh python scripts/02-ask-equivalence.py \
  --mutants-dir programs/factorial/mutants \
  --session FACTORIAL \
  --last 2

# ProteumIM window on the current display.
scripts/container.sh proteumim

# Rebuild after requirements.txt or the Dockerfile changes.
scripts/container.sh --build bash
```

A CLI-only command does not need a window. `proteumim` does. If the window does not appear, run `xhost +SI:localuser:$USER` on the host and start it again. On SELinux, a denial on `/tmp/.X11-unix` is fixed for this container with `docker compose run --security-opt label=disable`.
