set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15 CHARGED_NO_MIN=2.65 EXACT_BUMP_IMAGES=1 HBOND_MULTIPLE=1
id=X7e382cb
GALLOP_STOL=.30 python /app/work/warm_gallop.py $id 100 /app/work/$id/search_centro100/best.xml /app/work/$id/search_centro100/model.json > /app/work/$id/warm100.log 2>&1
BUMP_COEFF=150 HBOND_COEFF=20 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='1,2;0;1,2;0' python /app/work/search_conditional.py $id 100 101 > /app/work/$id/conditional101.log 2>&1
python /app/work/import_gallop.py $id 101 > /app/work/$id/import_g101.log 2>&1
python /app/work/add_ammonium_h.py $id g101 ionH101 /app/work/$id/search_g101/best.xml > /app/work/$id/addH101.log 2>&1
PACKING_SIGMA=.008 python /app/work/refine_obj.py $id ionH101 /app/work/$id/search_ionH101/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_ionH101.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_ionH101.cif --check > /app/work/$id/check_ionH101.log 2>&1
