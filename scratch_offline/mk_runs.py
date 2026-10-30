"""Create one fat-seed RUN dir per 6-sense chunk of ids_all.txt[start:end]."""
import subprocess, sys
start, end = int(sys.argv[1]), int(sys.argv[2])
ids = open('/tmp/claude-0/ids_all.txt').read().split()[start:end]
for i in range(0, len(ids), 6):
    chunk = ids[i:i + 6]
    run = f'data/exercise_seeding/ja/wf/r{start + i:05d}'
    for cmd in (['scripts/export_exercise_worklist.py', '--language', 'ja', '--format', 'csv',
                 '--sense-ids', ','.join(chunk), '--out-dir', run],
                ['scripts/fat_seed_runner.py', 'brief', run, '--width', '6']):
        r = subprocess.run(['python3', 'scratch_offline/run.py', *cmd], capture_output=True, text=True,
                           env={'PYTHONIOENCODING': 'utf-8', 'PATH': '/usr/bin:/bin:/usr/local/bin'})
        if r.returncode:
            print('FAIL', run, r.stderr[-300:]); break
    print(run, ','.join(chunk), flush=True)
