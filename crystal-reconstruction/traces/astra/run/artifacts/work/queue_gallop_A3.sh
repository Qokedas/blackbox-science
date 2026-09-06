export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/5191/status ]] && ! grep -q '^State:.*Z' /proc/5191/status; do sleep 5;done
SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.25 CONF_RANK=0 python /app/work/search_gallop.py X4f6fe58 11 2 --prepare --hscatter > /app/work/X4f6fe58/gallop11.log 2>&1
python /app/work/import_gallop.py X4f6fe58 11 > /app/work/X4f6fe58/import_g11.log 2>&1
python /app/work/refine_obj.py X4f6fe58 g11 /app/work/X4f6fe58/search_g11/best.xml --scale --tight > /app/work/X4f6fe58/refine_g11.log 2>&1
SEARCH_TIME=1800 PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.25 python /app/work/search_gallop.py X3f4781b 11 2 --prepare --hscatter > /app/work/X3f4781b/gallop11.log 2>&1
python /app/work/import_gallop.py X3f4781b 11 > /app/work/X3f4781b/import_g11.log 2>&1
python /app/work/refine_obj.py X3f4781b g11 /app/work/X3f4781b/search_g11/best.xml --scale --tight > /app/work/X3f4781b/refine_g11.log 2>&1
SEARCH_TIME=2200 PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.25 python /app/work/search_gallop.py X9af54a2 11 2 --prepare --hscatter > /app/work/X9af54a2/gallop11.log 2>&1
python /app/work/import_gallop.py X9af54a2 11 > /app/work/X9af54a2/import_g11.log 2>&1
python /app/work/refine_obj.py X9af54a2 g11 /app/work/X9af54a2/search_g11/best.xml --scale --tight > /app/work/X9af54a2/refine_g11.log 2>&1
