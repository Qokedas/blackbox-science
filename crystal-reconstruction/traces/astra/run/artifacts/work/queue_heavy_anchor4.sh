set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/38122/status ]] && ! grep -q '^State:.*Z' /proc/38122/status;do sleep 5;done
HEAVY_ANCHOR=/app/work/X4f6fe58/gallop_11/heavy_pool.npz HEAVY_ANCHOR_COEFF=30 HEAVY_ANCHOR_TOL=.35 HEAVY_POOL=/app/work/X4f6fe58/gallop_11/heavy_pool.npz HBOND_COEFF=15 BUMP_COEFF=40 START_REFL=100 SEARCH_TIME=1700 PARTICLES=128 ITERATIONS=400 CONF_RANK=0 GALLOP_STOL=.26 python /app/work/search_gallop.py X4f6fe58 41 2 --prepare --hscatter --packing > /app/work/X4f6fe58/gallop41.log 2>&1
python /app/work/import_gallop.py X4f6fe58 41 > /app/work/X4f6fe58/import_g41.log 2>&1
python /app/work/refine_obj.py X4f6fe58 g41 /app/work/X4f6fe58/search_g41/best.xml --scale --tight --stol=.38 > /app/work/X4f6fe58/refine_g41.log 2>&1
python /app/work/submit.py X4f6fe58 /app/work/X4f6fe58/refined_g41.cif --check > /app/work/X4f6fe58/check_g41.log 2>&1
