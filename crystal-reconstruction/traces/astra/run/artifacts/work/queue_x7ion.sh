set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15
while [[ -r /proc/41900/status ]] && ! grep -q '^State:.*Z' /proc/41900/status;do sleep 5;done
id=X7e382cb
GALLOP_STOL=.29 python /app/work/warm_gallop.py $id 41 /app/work/$id/refined_g40.xml /app/work/$id/search_g40/model.json > /app/work/$id/warm41.log 2>&1
EXACT_BUMP_IMAGES=1 HBOND_MULTIPLE=1 HBOND_COEFF=20 BUMP_COEFF=150 SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=450 START_NPZ=/app/work/$id/gallop_41/warm.npz START_JITTER=.10 START_TOR_JITTER=.45 MACRO_ELITE_FRAC=.45 python /app/work/search_gallop.py $id 41 1 --hscatter --packing > /app/work/$id/gallop41.log 2>&1
python /app/work/import_gallop.py $id 41 > /app/work/$id/import_g41.log 2>&1
python /app/work/refine_obj.py $id g41 /app/work/$id/search_g41/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g41.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g41.cif --check > /app/work/$id/check_g41.log 2>&1
