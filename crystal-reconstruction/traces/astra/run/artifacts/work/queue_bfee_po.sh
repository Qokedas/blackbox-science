export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
set -e
id=Xbfeeda9
while [[ ! -f /app/work/$id/refined_g11.json ]];do sleep 5;done
python /app/work/add_fixed_march.py $id g11md /app/work/$id/refined_g11.xml 1.32295 0 0 1 /app/work/$id/search_g11/model.json > /app/work/$id/md_add.log 2>&1
python /app/work/refine_obj.py $id g11md /app/work/$id/search_g11md/best.xml --scale --tight --free-march --stol=.35 > /app/work/$id/refine_g11md.log 2>&1
# Avoid an eighth long global search: wait for the psilocybin continuation.
while [[ -r /proc/36093/status ]] && ! grep -q '^State:.*Z' /proc/36093/status;do sleep 5;done
GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 60 /app/work/$id/refined_g11md.xml /app/work/$id/search_g11md/model.json > /app/work/$id/warm60.log 2>&1
SEARCH_TIME=2000 PARTICLES=128 ITERATIONS=400 BUMP_COEFF=60 HBOND_COEFF=12 START_NPZ=/app/work/$id/gallop_60/warm.npz START_JITTER=.08 START_TOR_JITTER=.40 MACRO_ELITE_FRAC=.35 python /app/work/search_gallop.py $id 60 1 --hscatter --packing > /app/work/$id/gallop60.log 2>&1
python /app/work/import_gallop.py $id 60 > /app/work/$id/import_g60.log 2>&1
python /app/work/refine_obj.py $id g60 /app/work/$id/search_g60/best.xml --scale --tight --free-march --stol=.4 > /app/work/$id/refine_g60.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g60.cif --check > /app/work/$id/check_g60.log 2>&1
