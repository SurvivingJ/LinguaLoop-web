#!/bin/bash
# Reference copies of the N3 upload/render drivers (paths point at the session scratchpad; adjust before reuse).
# Upload one finished fat-seed run live: assemble -> core -> exercises (renders exercise rows with the
# production judges via OpenRouter). Idempotent per run: a marker file prevents a second upload.
set -u
RUN="$1"
cd /home/user/LinguaLoop-web || exit 1
[ -f "$RUN/.live_uploaded" ] && { echo "$RUN already uploaded"; exit 0; }
grep -q "final reviewed check" "$RUN/fat_seed/nt_pipeline.log" 2>/dev/null || { echo "$RUN not finished"; exit 0; }
LOG="$RUN/live_upload.log"
python3 scripts/fat_seed_runner.py assemble "$RUN" >> "$LOG" 2>&1
U="$RUN/07_upload"
[ -f "$U/batch_001.core.json" ] || { echo "$RUN: nothing assembled"; exit 0; }
python scripts/upload_exercises.py --stage core --source-model claude-code:fat-seed --no-render \
  --batch-file "$U/batch_001.core.batch.json" --answers-file "$U/batch_001.core.json" >> "$LOG" 2>&1 \
  || { echo "$RUN: CORE FAILED"; exit 1; }
python scripts/upload_exercises.py --stage exercises --source-model claude-code:fat-seed --no-render \
  --batch-file "$U/batch_001.exercises.batch.json" --answers-file "$U/batch_001.exercises.json" >> "$LOG" 2>&1 \
  || { echo "$RUN: EXERCISES FAILED"; exit 1; }
date -u +%FT%TZ > "$RUN/.live_uploaded"
echo "$RUN uploaded: $(grep -c 'Stored prompt1_core' "$LOG") cores"
