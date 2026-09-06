set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/51460/status ]] && ! grep -q '^State:.*Z' /proc/51460/status;do sleep 5;done
id=Xedd9c7b
GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 84 /app/work/$id/refined_g52.xml /app/work/$id/search_g52/model.json > /app/work/$id/warm84.log 2>&1
BUMP_COEFF=80 HBOND_COEFF=15 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='0;1;0;1' python /app/work/search_conditional.py $id 84 85 > /app/work/$id/conditional85.log 2>&1
python /app/work/import_gallop.py $id 85 > /app/work/$id/import_g85.log 2>&1
python /app/work/refine_obj.py $id g85 /app/work/$id/search_g85/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g85.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g85.cif --check > /app/work/$id/check_g85.log 2>&1
