export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/8545/status ]] && ! grep -q '^State:.*Z' /proc/8545/status; do sleep 4; done
SEARCH_TIME=1000 PARTICLES=128 ITERATIONS=450 GALLOP_STOL=.25 python /app/work/search_gallop.py X7e382cb 22 1 --prepare --hscatter > /app/work/X7e382cb/gallop22.log 2>&1
python /app/work/import_gallop.py X7e382cb 22 > /app/work/X7e382cb/import_g22.log 2>&1
python /app/work/refine_obj.py X7e382cb g22 /app/work/X7e382cb/search_g22/best.xml --scale --tight --flexrings > /app/work/X7e382cb/refine_g22.log 2>&1
