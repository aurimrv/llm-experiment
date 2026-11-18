# Factorial

`factorial.c` reads one integer from the keyboard and prints its factorial. A negative number prints `Error!`.

```c
#include <stdio.h>
int main (void) {
  int value, number, fat;
  fat = 1;
  printf ("Input a number followed by a return: ");
  scanf ("%d", &value);
  number = value;
  if (number >= 0) {
    while (number > 1) {
      fat = fat * number;
      number--;
    }
    printf ("%d\n", fat);
  }
  else
    printf ("Error!\n");
  return 0;
}
```

The function under test is `main`, listed in `functions.txt`. The Proteum session name used below is `FACTORIAL`. Run the commands from the repository root, inside the container. `scripts/README.md` describes each flag.

## 1. Prepare the session

```bash
scripts/container.sh python scripts/01-prepare-program.py \
  --base-dir programs/factorial \
  --program factorial \
  --session FACTORIAL \
  --functions programs/factorial/functions.txt
```

This compiles `factorial.c` to `runner`, creates the session, builds the instrumented program `runner_instr`, generates the unit mutants, and writes `mutants/original_FACTORIAL.c` and `mutants/muta<N>_FACTORIAL.c`. Run it once. A second run fails because the session already exists.

## 2. Ask whether each mutant is equivalent

```bash
scripts/container.sh python scripts/02-ask-equivalence.py \
  --mutants-dir programs/factorial/mutants \
  --session FACTORIAL \
  --last 2
```

`--last 2` checks mutants 0, 1, and 2. Replace it with `--all` to check every mutant. The JSONL file is written under `programs/factorial/result/`. With the model in `.env.example`, that file is `openrouter__nvidia__nemotron-3-ultra-550b-a55b-free.jsonl`.

## 3. Export the CSV and the test set

```bash
scripts/container.sh python scripts/03-export-results.py \
  --program programs/factorial \
  --json programs/factorial/result/openrouter__nvidia__nemotron-3-ultra-550b-a55b-free.jsonl \
  --session FACTORIAL \
  --out testset
```

The CSV is saved next to the JSONL file. The test set is `programs/factorial/testset`. Factorial reads from the keyboard only, so each case is a `tecN.tes` file, such as `tec1.tes` containing `5` and a newline. The script does not write an `inputN.tes` file for this program. Duplicate inputs are stored once.

## 4. Run the test set

```bash
scripts/container.sh python scripts/04-run-testset.py \
  --program programs/factorial \
  --session FACTORIAL \
  --testset programs/factorial/testset
```

The script imports the test cases with the instrumented program so Proteum records the path, then runs:

```bash
exemuta -exec -trace -v . FACTORIAL
report -tcase -L 447 -S FACTORIAL_<timestamp> FACTORIAL
```

`-L 447` is the most detailed test-case report this Proteum build can write. The report file is `programs/factorial/FACTORIAL_<timestamp>.lst`. Importing again adds the same cases to the session.

## 5. List alive and dead mutants

```bash
scripts/container.sh python scripts/05-report-mutant-status.py \
  --program programs/factorial \
  --session FACTORIAL
```

The CSV is `programs/factorial/result/FACTORIAL-mutant-status.csv`. Each row is a mutant number and `alive` or `dead`.
