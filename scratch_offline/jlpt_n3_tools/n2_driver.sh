#!/bin/bash
# Upload finished N3 runs (no render) and render each with Claude judges (fail closed). Max 6 renders at once.
SP=/tmp/claude-0/-home-user-LinguaLoop-web/0e1641c0-ad03-567b-82e6-f8de70f47f61/scratchpad
R=/home/user/LinguaLoop-web/data/exercise_seeding/ja/wf_jlpt_n2
cd /home/user/LinguaLoop-web
export PATH=/home/user/LinguaLoop-web/scratch_offline/bin:$PATH CLAUDE_CLI_PATH=/home/user/LinguaLoop-web/scratch_offline/bin/claude
[ -f $SP/n2_STOP ] && exit 0
while true; do
  [ -f $SP/n2_STOP ] && { echo "STOP file present"; break; }
  for run in $R/r*; do
    n=$(basename $run)
    grep -q "final reviewed check" $run/fat_seed/nt_pipeline.log 2>/dev/null || continue
    if [ ! -f $run/.live_uploaded ]; then
      cap=$(cat $SP/n2_upload_cap 2>/dev/null || echo 0); up=$(ls $R/r*/.live_uploaded 2>/dev/null | wc -l)
      if [ "$up" -ge "$cap" ]; then [ -f $SP/n2_capped ] || echo "CAP $cap reached at $n; holding (DB check needed)"; touch $SP/n2_capped; continue; fi
      bash $SP/upload_run.sh $run
    fi
    [ -f $run/.live_uploaded ] || continue
    [ -f $SP/rerender_n2/$n.started ] && continue
    while [ $(pgrep -fc rerender_claude.py) -ge 6 ]; do sleep 20; done
    [ -f $SP/n2_STOP ] && break 2
    python3 -c "import csv;print('\n'.join(r['sense_id'] for r in csv.DictReader(open('$run/senses.csv'))))" > $SP/rerender_n2/$n.shard
    touch $SP/rerender_n2/$n.started
    ( python3 $SP/rerender_claude.py $SP/rerender_n2/$n.shard $SP/rerender_n2/$n.done > $SP/rerender_n2/$n.log 2>&1
      rc=$?; [ $rc -eq 3 ] && { touch $SP/n2_STOP; echo "$n render stopped: Claude unavailable"; }
      echo "$n rendered rc=$rc ok=$(grep -c '	ok	' $SP/rerender_n2/$n.done)" ) &
  done
  pgrep -f nt_pipeline.py >/dev/null || { all=1; for run in $R/r*; do grep -q "final reviewed check" $run/fat_seed/nt_pipeline.log 2>/dev/null && [ ! -f $SP/rerender_n2/$(basename $run).started ] && all=0; done; [ $all = 1 ] && { wait; echo "driver done"; break; }; }
  sleep 120
done
