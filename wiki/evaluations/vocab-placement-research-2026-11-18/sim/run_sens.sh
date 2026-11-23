#!/bin/bash
# Sensitivity runs (after the main run). All outputs under placement/sim/out.
S=/tmp/claude-0/-home-user-LinguaLoop-web/0e1641c0-ad03-567b-82e6-f8de70f47f61/scratchpad
SIM=$S/placement/sim/sim.py; SUM=$S/placement/sim/summarize.py; O=$S/placement/sim/out
cd /tmp
while pgrep -f "sim.py $S $O 500 main" >/dev/null; do sleep 20; done
python3 -I $SIM $S $O 500 main_rho designs=D2,D3,D4 && echo main_rho-done
python3 -I $SIM $S $O 300 eps06 sig_eps=0.6 designs=D0,D1,D1S,D3,D3S pops=zh:E:0.7,zh:J:0.7,ja:Z:0.7 && python3 -I $SUM $O/raw_eps06.json $O/tables_eps06.md
python3 -I $SIM $S $O 300 eps18 sig_eps=1.8 designs=D0,D1,D1S,D3,D3S pops=zh:E:0.7,zh:J:0.7,ja:Z:0.7 && python3 -I $SUM $O/raw_eps18.json $O/tables_eps18.md
python3 -I $SIM $S $O 300 partial partial=1 designs=D0,D2,D3,D3S pops=zh:E:0.7,zh:J:0.7,ja:E:0.7,ja:Z:0.7 && python3 -I $SUM $O/raw_partial.json $O/tables_partial.md
python3 -I $SIM $S $O 300 gamma25 gamma_max=2.5 designs=D0,D1,D1S,D1L,D3,D3S,D3L pops=zh:E:0.7,ja:E:0.7 && python3 -I $SUM $O/raw_gamma25.json $O/tables_gamma25.md
echo all-sens-done
