set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CANDIDATE_FILE=/app/work/X7e382cb/candidates_subother.json SG_SCAN=0
for i in 0 1 2;do CANDIDATE_INDEX=$i python /app/work/fit_candidate.py X7e382cb subother$i .35 > /app/work/X7e382cb/fit_subother$i.log 2>&1;done
