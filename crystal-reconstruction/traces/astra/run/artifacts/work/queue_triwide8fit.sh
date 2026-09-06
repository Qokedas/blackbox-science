export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for i in 0 1 2 5;do
 CANDIDATE_FILE=/app/work/X8a6f5a8/index_triwide_p1.json CANDIDATE_INDEX=$i SG_SCAN=0 python /app/work/fit_candidate.py X8a6f5a8 triwide$i .32 > /app/work/X8a6f5a8/fit_triwide$i.log 2>&1
done
