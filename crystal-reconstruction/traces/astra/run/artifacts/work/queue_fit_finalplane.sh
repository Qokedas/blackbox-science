export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CANDIDATE_FILE=/app/work/X1db5091/candidates_finalplane.json SG_SCAN=0
for i in 2 3;do CANDIDATE_INDEX=$i python /app/work/fit_candidate.py X1db5091 final$i .38 > /app/work/X1db5091/fit_final$i.log 2>&1;done
