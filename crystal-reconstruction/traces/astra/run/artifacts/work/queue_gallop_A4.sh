export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/15174/status ]] && ! grep -q '^State:.*Z' /proc/15174/status; do sleep 5; done
for id in Xbfeeda9 X35b7fbc Xe1fb77b X019b9a4; do
 model=; secs=2300; [[ $id == X35b7fbc ]] && model=--model=/app/work/X35b7fbc/cis.json
 SEARCH_TIME=$secs PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.24 CONF_RANK=0 python /app/work/search_gallop.py $id 11 1 --prepare --hscatter $model > /app/work/$id/gallop11.log 2>&1
 python /app/work/import_gallop.py $id 11 > /app/work/$id/import_g11.log 2>&1
 python /app/work/refine_obj.py $id g11 /app/work/$id/search_g11/best.xml --scale --tight > /app/work/$id/refine_g11.log 2>&1
done
