set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/39221/status ]] && ! grep -q '^State:.*Z' /proc/39221/status;do sleep 5;done
id=Xb7088cf
mkdir -p /app/work/$id/search_chem11
cp /app/work/$id/search_g11/model.json /app/work/$id/search_chem11/model.json
python /app/work/refine_obj.py $id chem11 /app/work/$id/refined_g11.xml --scale --tight --stol=.38 > /app/work/$id/refine_chem11.log 2>&1
GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 50 /app/work/$id/refined_chem11.xml /app/work/$id/search_chem11/model.json > /app/work/$id/warm50.log 2>&1
SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=450 BUMP_COEFF=70 HBOND_COEFF=15 START_NPZ=/app/work/$id/gallop_50/warm.npz START_JITTER=.10 START_TOR_JITTER=.45 MACRO_ELITE_FRAC=.4 python /app/work/search_gallop.py $id 50 1 --hscatter --packing > /app/work/$id/gallop50.log 2>&1
python /app/work/import_gallop.py $id 50 > /app/work/$id/import_g50.log 2>&1
python /app/work/refine_obj.py $id g50 /app/work/$id/search_g50/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g50.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g50.cif --check > /app/work/$id/check_g50.log 2>&1
