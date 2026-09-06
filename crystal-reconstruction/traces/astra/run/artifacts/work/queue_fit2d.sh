export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/9704/status ]] && ! grep -q '^State:.*Z' /proc/9704/status; do sleep 3;done
for x in 'X8a06d7a 0' 'X8a06d7a 1' 'X263b09a 0' 'X263b09a 1' 'X14a2b08 0'; do
 set -- $x
 CANDIDATE_FILE=/app/work/$1/candidates_2d.json CANDIDATE_INDEX=$2 python /app/work/fit_candidate.py $1 2d$2 .38 > /app/work/$1/fit_2d$2.log 2>&1
done
