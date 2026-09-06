set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15 CHARGED_NO_MIN=2.65 EXACT_BUMP_IMAGES=1 HBOND_MULTIPLE=1
while [[ -r /proc/55083/status ]] && ! grep -q '^State:.*Z' /proc/55083/status;do sleep 5;done
id=X7e382cb
mkdir -p /app/work/$id/gallop_88
cp /app/work/$id/base.xml /app/work/$id/gallop_88/base.xml
BASE_XML=/app/work/$id/gallop_88/base.xml BUMP_COEFF=150 HBOND_COEFF=20 SEARCH_TIME=1500 START_REFL=90 PARTICLES=160 ITERATIONS=400 GALLOP_STOL=.29 CONF_RANK=1 python /app/work/search_gallop.py $id 88 1 --prepare --hscatter --packing > /app/work/$id/gallop88.log 2>&1
python /app/work/import_gallop.py $id 88 > /app/work/$id/import_g88.log 2>&1
python /app/work/add_ammonium_h.py $id g88 ionH88 /app/work/$id/search_g88/best.xml > /app/work/$id/addH88.log 2>&1
python /app/work/refine_obj.py $id ionH88 /app/work/$id/search_ionH88/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_ionH88.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_ionH88.cif --check > /app/work/$id/check_ionH88.log 2>&1
