export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/21574/status ]] && ! grep -q '^State:.*Z' /proc/21574/status; do sleep 5; done
SEARCH_TIME=350 PARTICLES=384 ITERATIONS=450 python /app/work/solve_heavy.py X4f6fe58 11 > /app/work/X4f6fe58/heavy11.log 2>&1
HEAVY_POOL=/app/work/X4f6fe58/gallop_11/heavy_pool.npz SEARCH_TIME=1600 PARTICLES=128 ITERATIONS=400 CONF_RANK=4 GALLOP_STOL=.25 python /app/work/search_gallop.py X4f6fe58 40 2 --prepare --hscatter > /app/work/X4f6fe58/gallop40.log 2>&1
python /app/work/import_gallop.py X4f6fe58 40 > /app/work/X4f6fe58/import_g40.log 2>&1
python /app/work/refine_obj.py X4f6fe58 g40 /app/work/X4f6fe58/search_g40/best.xml --scale --tight > /app/work/X4f6fe58/refine_g40.log 2>&1
