export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
SEARCH_TIME=1600 PARTICLES=128 ITERATIONS=400 MACRO_ELITE_FRAC=.30 START_NPZ=/app/work/X4f6fe58/gallop_11/best.npz START_JITTER=.15 START_TOR_JITTER=.6 python /app/work/search_gallop.py X4f6fe58 31 2 --hscatter --packing > /app/work/X4f6fe58/gallop31.log 2>&1
python /app/work/import_gallop.py X4f6fe58 31 > /app/work/X4f6fe58/import_g31.log 2>&1
python /app/work/refine_obj.py X4f6fe58 g31 /app/work/X4f6fe58/search_g31/best.xml --scale --tight > /app/work/X4f6fe58/refine_g31.log 2>&1
