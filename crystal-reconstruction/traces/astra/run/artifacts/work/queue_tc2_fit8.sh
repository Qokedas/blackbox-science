export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/23194/status ]] && ! grep -q '^State:.*Z' /proc/23194/status; do sleep 5;done
SEARCH_TIME=950 BUMP_COEFF=150 PARTICLES=192 ITERATIONS=450 BATCHES=50 python /app/work/solve_twocentres.py tc2 > /app/work/X7e382cb/tc2.log 2>&1
for i in 0 1 2 3;do CANDIDATE_FILE=/app/work/X8a6f5a8/candidates_wide.json CANDIDATE_INDEX=$i SG_SCAN=0 python /app/work/fit_candidate.py X8a6f5a8 wide$i .35 > /app/work/X8a6f5a8/fit_wide$i.log 2>&1;done
SELECT_FILE=/app/work/X8a6f5a8/peak_select_ext2.json NPEAK=30 NSPUR=2 TTHERR=.04 TRIALS=100 INDEX_TIME=750 VMIN=1200 VMAX=3200 VTARGET=2200 AMAX=32 HMAX=8 INDEX_TAG=triwide python /app/work/index_metric.py X8a6f5a8 TRICLINIC P > /app/work/X8a6f5a8/metric_triwide.log 2>&1
