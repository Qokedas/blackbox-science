set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/51725/status ]] && ! grep -q '^State:.*Z' /proc/51725/status;do sleep 5;done
id=X1a56c78
GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 82 /app/work/$id/refined_g18.xml /app/work/$id/search_g18/model.json > /app/work/$id/warm82.log 2>&1
BUMP_COEFF=70 HBOND_COEFF=20 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='1;0;1;0' python /app/work/search_conditional.py $id 82 83 > /app/work/$id/conditional83.log 2>&1
python /app/work/import_gallop.py $id 83 > /app/work/$id/import_g83.log 2>&1
python /app/work/refine_obj.py $id g83 /app/work/$id/search_g83/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g83.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g83.cif --check > /app/work/$id/check_g83.log 2>&1
