export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
BUMP_COEFF=200 EXACT_BUMP_IMAGES=1 SEARCH_TIME=700 PARTICLES=96 ITERATIONS=350 START_NPZ=/app/work/X7e382cb/gallop_31/best.npz START_JITTER=.08 START_TOR_JITTER=.5 MACRO_ELITE_FRAC=.35 python /app/work/search_gallop.py X7e382cb 32 1 --hscatter --packing > /app/work/X7e382cb/gallop32.log 2>&1
python /app/work/import_gallop.py X7e382cb 32 > /app/work/X7e382cb/import_g32.log 2>&1
python /app/work/refine_obj.py X7e382cb g32 /app/work/X7e382cb/search_g32/best.xml --scale --tight > /app/work/X7e382cb/refine_g32.log 2>&1
