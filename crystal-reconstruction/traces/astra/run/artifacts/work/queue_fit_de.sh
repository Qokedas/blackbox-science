export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for id in X14a2b08 X263b09a X8a06d7a; do
 for i in 0 1 2; do
  export CANDIDATE_FILE=/app/work/$id/index_de_raw.json CANDIDATE_INDEX=$i
  python /app/work/fit_candidate.py $id de$i .27 > /app/work/$id/fit_de$i.log 2>&1
 done
done
