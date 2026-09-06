export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/11003/status ]] && ! grep -q '^State:.*Z' /proc/11003/status; do sleep 4;done
SEARCH_TIME=1400 PARTICLES=224 ITERATIONS=550 BATCHES=60 python /app/work/solve_twocentres.py tc1 > /app/work/X7e382cb/tc1.log 2>&1
