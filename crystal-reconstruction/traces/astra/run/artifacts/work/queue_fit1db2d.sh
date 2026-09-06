export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CANDIDATE_FILE=/app/work/X1db5091/candidates_2dlarge.json
for i in 0 1 2 3 4 5 6 7;do CANDIDATE_INDEX=$i python /app/work/fit_candidate.py X1db5091 plane$i .36 > /app/work/X1db5091/fit_plane$i.log 2>&1;done
