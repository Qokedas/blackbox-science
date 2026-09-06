set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15
while [[ -r /proc/47634/status ]] && ! grep -q '^State:.*Z' /proc/47634/status;do sleep 5;done
id=X7e382cb
python /app/work/add_ammonium_h.py $id g41 ionH41 > /app/work/$id/addH41.log 2>&1
python /app/work/refine_obj.py $id ionH41 /app/work/$id/search_ionH41/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_ionH41.log 2>&1
GALLOP_STOL=.29 python /app/work/warm_gallop.py $id 84 /app/work/$id/refined_ionH41.xml /app/work/$id/search_ionH41/model.json > /app/work/$id/warm84.log 2>&1
EXACT_BUMP_IMAGES=1 HBOND_MULTIPLE=1 BUMP_COEFF=150 HBOND_COEFF=20 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='1,2,4,5;0;3;1,2,4,5;0;3' python /app/work/search_conditional.py $id 84 85 > /app/work/$id/conditional85.log 2>&1
python /app/work/import_gallop.py $id 85 > /app/work/$id/import_g85.log 2>&1
python /app/work/add_ammonium_h.py $id g85 ionH85 /app/work/$id/search_g85/best.xml > /app/work/$id/addH85.log 2>&1
python /app/work/refine_obj.py $id ionH85 /app/work/$id/search_ionH85/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_ionH85.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_ionH85.cif --check > /app/work/$id/check_ionH85.log 2>&1
