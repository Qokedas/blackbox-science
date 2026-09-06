export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for id in Xedd9c7b Xb7088cf; do
 for idx in 0 1 2; do CANDIDATE_INDEX=$idx python /app/work/fit_candidate.py $id raw$idx .30 > /app/work/$id/fit_raw$idx.log 2>&1; done
done
