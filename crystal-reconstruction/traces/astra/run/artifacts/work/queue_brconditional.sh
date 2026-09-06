set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X4f6fe58
mkdir -p /app/work/$id/search_chem11
cp /app/work/$id/search_g11/model.json /app/work/$id/search_chem11/model.json
python /app/work/refine_obj.py $id chem11 /app/work/$id/refined_g11.xml --scale --tight --stol=.38 > /app/work/$id/refine_chem11.log 2>&1
# No partial-heavy-atom positional prior is retained.
GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 82 /app/work/$id/refined_chem11.xml /app/work/$id/search_chem11/model.json > /app/work/$id/warm82.log 2>&1
BUMP_COEFF=70 HBOND_COEFF=12 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='0;1;0;1' python /app/work/search_conditional.py $id 82 83 > /app/work/$id/conditional83.log 2>&1
python /app/work/import_gallop.py $id 83 > /app/work/$id/import_g83.log 2>&1
python /app/work/refine_obj.py $id g83 /app/work/$id/search_g83/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g83.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g83.cif --check > /app/work/$id/check_g83.log 2>&1
