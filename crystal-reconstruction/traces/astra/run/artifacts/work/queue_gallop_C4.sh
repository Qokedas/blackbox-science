export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/7272/status ]] && ! grep -q '^State:.*Z' /proc/7272/status; do sleep 5; done
for id in X263b09a X14a2b08; do
 SEARCH_TIME=2400 PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.25 CONF_RANK=0 python /app/work/search_gallop.py $id 11 1 --prepare --hscatter > /app/work/$id/gallop11.log 2>&1
 python /app/work/import_gallop.py $id 11 > /app/work/$id/import_g11.log 2>&1
 python /app/work/refine_obj.py $id g11 /app/work/$id/search_g11/best.xml --scale --tight > /app/work/$id/refine_g11.log 2>&1
done
MAX_STOL=.32 python /app/work/create_stable_base.py X1db5091 final2 'P 1 21/c 1' --submit > /app/work/X1db5091/basefresh.log 2>&1
SEARCH_TIME=2800 PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.25 CONF_RANK=0 python /app/work/search_gallop.py X1db5091 11 1 --prepare --hscatter > /app/work/X1db5091/gallop11.log 2>&1
python /app/work/import_gallop.py X1db5091 11 > /app/work/X1db5091/import_g11.log 2>&1
python /app/work/refine_obj.py X1db5091 g11 /app/work/X1db5091/search_g11/best.xml --scale --tight > /app/work/X1db5091/refine_g11.log 2>&1
