set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=3
id=X1db5091
GALLOP_STOL=.31 python /app/work/warm_gallop.py $id 102 /app/work/$id/refined_g50.xml /app/work/$id/search_g50/model.json > /app/work/$id/warm102.log 2>&1
BUMP_COEFF=80 HBOND_COEFF=30 PARTICLES=96 ITERATIONS=320 FREE_SCHEDULE='1;0;1;0' python /app/work/search_conditional.py $id 102 103 > /app/work/$id/conditional103.log 2>&1
python /app/work/import_gallop.py $id 103 > /app/work/$id/import_g103.log 2>&1
python /app/work/refine_obj.py $id g103 /app/work/$id/search_g103/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g103.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g103.cif --check > /app/work/$id/check_g103.log 2>&1
