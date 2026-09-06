set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X1db5091
GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 90 /app/work/$id/refined_g11.xml /app/work/$id/search_g11/model.json > /app/work/$id/warm90.log 2>&1
BUMP_COEFF=70 HBOND_COEFF=40 PARTICLES=96 ITERATIONS=300 FREE_SCHEDULE='1;1;1' python /app/work/search_conditional.py $id 90 91 > /app/work/$id/conditional91.log 2>&1
python /app/work/import_gallop.py $id 91 > /app/work/$id/import_g91.log 2>&1
python /app/work/refine_obj.py $id g91 /app/work/$id/search_g91/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g91.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g91.cif --check > /app/work/$id/check_g91.log 2>&1
