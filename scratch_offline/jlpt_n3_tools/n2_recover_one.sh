#!/bin/bash
# Re-assemble re-reviewed runs, upload ONLY the recovered senses (no render), then render them with Claude judges.
SP=/tmp/claude-0/-home-user-LinguaLoop-web/0e1641c0-ad03-567b-82e6-f8de70f47f61/scratchpad
cd /home/user/LinguaLoop-web
export PATH=/home/user/LinguaLoop-web/scratch_offline/bin:$PATH CLAUDE_CLI_PATH=/home/user/LinguaLoop-web/scratch_offline/bin/claude
for run in "$@"; do
  n=$(basename $run); [ -f $run/.recovered ] && continue
  [ -d $run/07_upload_wave1 ] || mv $run/07_upload $run/07_upload_wave1
  rm -rf $run/07_upload
  python3 scripts/fat_seed_runner.py assemble $run >> $run/live_upload_recovered.log 2>&1
  python3 - "$run" "$SP/n2_rereview.json" > $SP/rerender_n2/$n.recover.shard <<'PY'
import json, sys
run, plan = sys.argv[1], sys.argv[2]
want = set(json.load(open(plan))[run]); U = f'{run}/07_upload'
try:
    got = {str(a['sense_id']) for a in json.load(open(f'{U}/batch_001.core.json'))}
except FileNotFoundError:
    got = set()
keep = want & got
for stem in ('core', 'exercises'):
    try:
        b = json.load(open(f'{U}/batch_001.{stem}.batch.json')); a = json.load(open(f'{U}/batch_001.{stem}.json'))
    except FileNotFoundError:
        continue
    b['items'] = [i for i in b['items'] if str(i['sense_id']) in keep]; b['count'] = len(b['items'])
    a = [i for i in a if str(i['sense_id']) in keep]
    json.dump(b, open(f'{U}/recover.{stem}.batch.json', 'w'), ensure_ascii=False)
    json.dump(a, open(f'{U}/recover.{stem}.json', 'w'), ensure_ascii=False)
print('\n'.join(sorted(keep)))
PY
  k=$(grep -c . $SP/rerender_n2/$n.recover.shard)
  if [ "$k" -gt 0 ]; then
    U=$run/07_upload; L=$run/live_upload_recovered.log
    python scripts/upload_exercises.py --stage core --no-render --source-model claude-code:fat-seed --batch-file $U/recover.core.batch.json --answers-file $U/recover.core.json >> $L 2>&1 \
     && python scripts/upload_exercises.py --stage exercises --no-render --source-model claude-code:fat-seed --batch-file $U/recover.exercises.batch.json --answers-file $U/recover.exercises.json >> $L 2>&1 \
     || { echo "$n RECOVER UPLOAD FAILED"; continue; }
    python3 $SP/rerender_claude.py $SP/rerender_n2/$n.recover.shard $SP/rerender_n2/$n.recover.done > $SP/rerender_n2/$n.recover.log 2>&1
    rc=$?; [ $rc -eq 3 ] && { echo "$n recover render stopped: Claude unavailable"; touch $SP/n2_STOP; exit 3; }
  fi
  touch $run/.recovered
  echo "$n recovered $k of $(python3 -c "import json;print(len(json.load(open('$SP/n2_rereview.json'))['$run']))") ok=$(grep -c '	ok	' $SP/rerender_n2/$n.recover.done 2>/dev/null)"
done

