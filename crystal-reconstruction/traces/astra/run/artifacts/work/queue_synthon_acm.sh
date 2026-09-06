export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/25595/status ]] && ! grep -q '^State:.*Z' /proc/25595/status;do sleep 5;done
for id in X263b09a X14a2b08; do
 START_REFL=140 RAMP_REF_EVERY=4 RAMP_REF_STEP=50 SEARCH_TIME=1400 PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.25 HBOND_COEFF=8 python /app/work/search_gallop.py $id 70 1 --prepare --hscatter --packing --model=/app/work/$id/synthon.json > /app/work/$id/gallop70.log 2>&1
 python /app/work/import_gallop.py $id 70 > /app/work/$id/import_g70.log 2>&1
 PACKING_SIGMA=.025 python /app/work/refine_obj.py $id g70 /app/work/$id/search_g70/best.xml --scale --tight --packing --stol=.35 > /app/work/$id/refine_g70.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_g70.cif --check > /app/work/$id/check_g70.log 2>&1
 done
