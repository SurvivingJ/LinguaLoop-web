#!/bin/bash
# Reference copies of the N3 upload/render drivers (paths point at the session scratchpad; adjust before reuse).
# Upload finished N3 runs (no render) and render each with Claude judges (fail closed). Max 6 renders at once.
SP=/tmp/claude-0/-home-user-LinguaLoop-web/0e1641c0-ad03-567b-82e6-f8de70f47f61/scratchpad
R=/home/user/LinguaLoop-web/data/exercise_seeding/ja/wf_jlpt_n3
cd /home/user/LinguaLoop-web
[ -f $SP/n3_STOP ] && exit 0
while true; do
  [ -f $SP/n3_STOP ] && { echo "STOP file present"; break; }
  for run in $R/r*; do
    n=$(basename $run)
    grep -q "final reviewed check" $run/fat_seed/nt_pipeline.log 2>/dev/null || continue
    if [ ! -f $run/.live_uploaded ]; then bash $SP/upload_run.sh $run; fi
    [ -f $run/.live_uploaded ] || continue
    [ -f $SP/rerender_n3/$n.started ] && continue
    while [ $(pgrep -fc rerender_claude.py) -ge 6 ]; do sleep 20; done
    [ -f $SP/n3_STOP ] && break 2
    python3 -c "import csv;print('\n'.join(r['sense_id'] for r in csv.DictReader(open('$run/senses.csv'))))" > $SP/rerender_n3/$n.shard
    touch $SP/rerender_n3/$n.started
    ( python3 $SP/rerender_claude.py $SP/rerender_n3/$n.shard $SP/rerender_n3/$n.done > $SP/rerender_n3/$n.log 2>&1
      rc=$?; [ $rc -eq 3 ] && { touch $SP/n3_STOP; echo "$n render stopped: Claude unavailable"; }
      echo "$n rendered rc=$rc ok=$(grep -c '	ok	' $SP/rerender_n3/$n.done)" ) &
  done
  pgrep -f nt_pipeline.py >/dev/null || { all=1; for run in $R/r*; do grep -q "final reviewed check" $run/fat_seed/nt_pipeline.log 2>/dev/null && [ ! -f $SP/rerender_n3/$(basename $run).started ] && all=0; done; [ $all = 1 ] && { wait; echo "driver done"; break; }; }
  sleep 120
done
