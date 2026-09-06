set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CARBONYL_OO_MIN=2.85 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=4
while [[ -r /proc/51579/status ]] && ! grep -q '^State:.*Z' /proc/51579/status;do sleep 5;done
id=X4f6fe58
mkdir -p /app/work/$id/search_chem83
cp /app/work/$id/search_g83/model.json /app/work/$id/search_chem83/model.json
python /app/work/refine_obj.py $id chem83 /app/work/$id/refined_g83.xml --scale --tight --stol=.4 > /app/work/$id/refine_chem83.log 2>&1
GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 84 /app/work/$id/refined_chem83.xml /app/work/$id/search_chem83/model.json > /app/work/$id/warm84.log 2>&1
SEARCH_TIME=1600 BUMP_COEFF=80 HBOND_COEFF=15 PARTICLES=128 ITERATIONS=400 START_NPZ=/app/work/$id/gallop_84/warm.npz START_JITTER=.12 START_TOR_JITTER=.4 MACRO_ELITE_FRAC=.5 python /app/work/search_gallop.py $id 84 1 --hscatter --packing > /app/work/$id/gallop84.log 2>&1
python /app/work/import_gallop.py $id 84 > /app/work/$id/import_g84.log 2>&1
python /app/work/refine_obj.py $id g84 /app/work/$id/search_g84/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g84.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g84.cif --check > /app/work/$id/check_g84.log 2>&1
