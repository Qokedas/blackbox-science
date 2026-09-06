set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X263b09a
BUMP_COEFF=70 HBOND_COEFF=80 PARTICLES=128 ITERATIONS=350 BATCHES=3 python /app/work/search_coformer.py $id 90 91 > /app/work/$id/coformer91.log 2>&1
python /app/work/import_gallop.py $id 91 > /app/work/$id/import_g91.log 2>&1
python /app/work/refine_obj.py $id g91 /app/work/$id/search_g91/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g91.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g91.cif --check > /app/work/$id/check_g91.log 2>&1
