export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/31937/status ]] && ! grep -q '^State:.*Z' /proc/31937/status; do sleep 5;done
for id in X263b09a X14a2b08;do
 while [[ ! -f /app/work/$id/refined_g11.json ]];do sleep 5;done
 python /app/work/guided_synthon.py $id g11 synseed > /app/work/$id/guided_synthon.log 2>&1
 GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 71 /app/work/$id/search_synseed/best.xml /app/work/$id/search_synseed/model.json > /app/work/$id/warm71.log 2>&1
 SEARCH_TIME=1400 PARTICLES=128 ITERATIONS=450 HBOND_COEFF=8 BUMP_COEFF=60 START_NPZ=/app/work/$id/gallop_71/warm.npz START_JITTER=.08 START_TOR_JITTER=.35 MACRO_ELITE_FRAC=.35 python /app/work/search_gallop.py $id 71 1 --hscatter --packing > /app/work/$id/gallop71.log 2>&1
 python /app/work/import_gallop.py $id 71 > /app/work/$id/import_g71.log 2>&1
 python /app/work/refine_obj.py $id g71 /app/work/$id/search_g71/best.xml --scale --tight --stol=.38 > /app/work/$id/refine_g71.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_g71.cif --check > /app/work/$id/check_g71.log 2>&1
done
