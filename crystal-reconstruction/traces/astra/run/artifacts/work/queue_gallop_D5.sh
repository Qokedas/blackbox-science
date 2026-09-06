export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/16582/status ]] && ! grep -q '^State:.*Z' /proc/16582/status; do sleep 5; done
python /app/work/import_gallop.py X13023e3 31 > /app/work/X13023e3/import_g31.log 2>&1
python /app/work/refine_obj.py X13023e3 g31 /app/work/X13023e3/search_g31/best.xml --scale --tight > /app/work/X13023e3/refine_g31.log 2>&1
SEARCH_TIME=2200 PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.23 CONF_RANK=0 python /app/work/search_gallop.py Xedd9c7b 11 2 --prepare --hscatter > /app/work/Xedd9c7b/gallop11.log 2>&1
python /app/work/import_gallop.py Xedd9c7b 11 > /app/work/Xedd9c7b/import_g11.log 2>&1
python /app/work/refine_obj.py Xedd9c7b g11 /app/work/Xedd9c7b/search_g11/best.xml --scale --tight > /app/work/Xedd9c7b/refine_g11.log 2>&1
for id in X1a56c78 X8a06d7a; do
 SEARCH_TIME=2200 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.24 CONF_RANK=0 python /app/work/search_gallop.py $id 11 1 --prepare --hscatter > /app/work/$id/gallop11.log 2>&1
 python /app/work/import_gallop.py $id 11 > /app/work/$id/import_g11.log 2>&1
 python /app/work/refine_obj.py $id g11 /app/work/$id/search_g11/best.xml --scale --tight > /app/work/$id/refine_g11.log 2>&1
done
