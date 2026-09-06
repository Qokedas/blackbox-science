export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/7958/status ]] && ! grep -q '^State:.*Z' /proc/7958/status; do sleep 5; done
SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=450 GALLOP_STOL=.25 python /app/work/search_gallop.py X7e382cb 21 1 --prepare > /app/work/X7e382cb/gallop21.log 2>&1
python /app/work/import_gallop.py X7e382cb 21 > /app/work/X7e382cb/import_g21.log 2>&1
python /app/work/refine_obj.py X7e382cb g21 /app/work/X7e382cb/search_g21/best.xml --scale > /app/work/X7e382cb/refine_g21.log 2>&1
