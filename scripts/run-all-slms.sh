#!/usr/bin/env bash
# run-all-slms.sh
set -u

MODELS_FILE="${1:-slms.txt}"
PROGRAM="programs/factorial"
SESSION="FACTORIAL"
PROVIDER="ollama"

failed=()

# Read the list into an array first, so nothing downstream can consume it
mapfile -t MODELS < <(tr -d '\r' < "$MODELS_FILE" | sed '/^[[:space:]]*$/d')

for model in "${MODELS[@]}"; do
  slug="${model//[:\/]/-}"
  json="${PROGRAM}/result/${PROVIDER}__${slug}.jsonl"

  echo "=== [$model] step 1: ask equivalence ==="
  if ! scripts/container.sh python scripts/02-ask-equivalence.py \
        --mutants-dir "${PROGRAM}/mutants" \
        --session "$SESSION" \
        --provider "$PROVIDER" \
        --model "$model" \
        --all < /dev/null; then
    echo "!!! [$model] step 1 failed, skipping export"
    failed+=("$model")
    continue
  fi

  echo "=== [$model] step 2: export results ==="
  if ! scripts/container.sh python scripts/03-export-results.py \
        --program "$PROGRAM" \
        --json "$json" \
        --session "$SESSION" \
        --out "testset-${slug}" < /dev/null; then
    echo "!!! [$model] step 2 failed"
    failed+=("$model")
  fi
done

if ((${#failed[@]})); then
  echo "Failed models: ${failed[*]}"
  exit 1
fi
echo "All models done."