export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/4263/status ]] && ! grep -q '^State:.*Z' /proc/4263/status; do sleep 5;done
SEARCH_TIME=2000 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.25 python /app/work/search_gallop.py Xd8634a2 11 1 --prepare --hscatter > /app/work/Xd8634a2/gallop11.log 2>&1
python /app/work/import_gallop.py Xd8634a2 11 > /app/work/Xd8634a2/import_g11.log 2>&1
python /app/work/refine_obj.py Xd8634a2 g11 /app/work/Xd8634a2/search_g11/best.xml --scale --tight > /app/work/Xd8634a2/refine_g11.log 2>&1
SEARCH_TIME=2000 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.25 python /app/work/search_gallop.py Xd4c1a35 11 2 --prepare --hscatter > /app/work/Xd4c1a35/gallop11.log 2>&1
python /app/work/import_gallop.py Xd4c1a35 11 > /app/work/Xd4c1a35/import_g11.log 2>&1
python /app/work/refine_obj.py Xd4c1a35 g11 /app/work/Xd4c1a35/search_g11/best.xml --scale --tight > /app/work/Xd4c1a35/refine_g11.log 2>&1
SEARCH_TIME=2000 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.25 python /app/work/search_gallop.py Xb7088cf 11 1 --prepare --hscatter > /app/work/Xb7088cf/gallop11.log 2>&1
python /app/work/import_gallop.py Xb7088cf 11 > /app/work/Xb7088cf/import_g11.log 2>&1
python /app/work/refine_obj.py Xb7088cf g11 /app/work/Xb7088cf/search_g11/best.xml --scale --tight > /app/work/Xb7088cf/refine_g11.log 2>&1
