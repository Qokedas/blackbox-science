export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CANDIDATE_FILE=/app/work/X8a6f5a8/candidates_metric.json
while [[ -r /proc/15347/status ]] && ! grep -q '^State:.*Z' /proc/15347/status; do sleep 2;done
for i in 0 1 2 3 4;do CANDIDATE_INDEX=$i python /app/work/fit_candidate.py X8a6f5a8 metric$i .33 > /app/work/X8a6f5a8/fit_metric$i.log 2>&1;done
