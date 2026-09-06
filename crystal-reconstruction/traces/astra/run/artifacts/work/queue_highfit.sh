export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/8407/status ]] && ! grep -q '^State:.*Z' /proc/8407/status; do sleep 5; done
for id in X8a06d7a X263b09a; do
 for idx in 0 1 2; do
  CANDIDATE_FILE=/app/work/$id/index_de_raw.json CANDIDATE_INDEX=$idx python /app/work/fit_candidate.py $id deh$idx .40 > /app/work/$id/fit_deh$idx.log 2>&1
 done
 for idx in 0; do CANDIDATE_FILE=/app/work/$id/candidates.json CANDIDATE_INDEX=$idx python /app/work/fit_candidate.py $id oldh$idx .40 > /app/work/$id/fit_oldh$idx.log 2>&1; done
done
