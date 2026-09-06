export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/34814/status ]] && ! grep -q '^State:.*Z' /proc/34814/status; do sleep 5;done
cp -r /app/work/Xedd9c7b/gallop_50 /app/work/Xedd9c7b/gallop_51
rm -f /app/work/Xedd9c7b/gallop_51/STOP
HBOND_COEFF=20 SEARCH_TIME=1400 PARTICLES=128 ITERATIONS=400 MACRO_ELITE_FRAC=.35 START_NPZ=/app/work/Xedd9c7b/gallop_50/best.npz START_JITTER=.06 START_TOR_JITTER=.35 python /app/work/search_gallop.py Xedd9c7b 51 1 --hscatter --packing > /app/work/Xedd9c7b/gallop51.log 2>&1
python /app/work/import_gallop.py Xedd9c7b 51 > /app/work/Xedd9c7b/import_g51.log 2>&1
python /app/work/refine_obj.py Xedd9c7b g51 /app/work/Xedd9c7b/search_g51/best.xml --scale --tight --stol=.38 > /app/work/Xedd9c7b/refine_g51.log 2>&1
python /app/work/submit.py Xedd9c7b /app/work/Xedd9c7b/refined_g51.cif --check > /app/work/Xedd9c7b/check_g51.log 2>&1
