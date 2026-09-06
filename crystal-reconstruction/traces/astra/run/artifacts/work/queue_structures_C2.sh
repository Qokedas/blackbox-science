export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/4266/status ]] && ! grep -q '^State:.*Z' /proc/4266/status; do sleep 5; done
SEARCH_TIME=1600 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.23 python /app/work/search_gallop.py X13023e3 11 1 --prepare > /app/work/X13023e3/gallop11.log 2>&1
python /app/work/import_gallop.py X13023e3 11 > /app/work/X13023e3/import_g11.log 2>&1
python /app/work/refine_obj.py X13023e3 g11 /app/work/X13023e3/search_g11/best.xml --scale > /app/work/X13023e3/refine_g11.log 2>&1
SEARCH_TIME=2200 MC_STEPS=4000000 TARGET_RW=.12 python /app/work/search_obj.py X263b09a 1 1 --rescale --profile > /app/work/X263b09a/search1.log 2>&1
python /app/work/refine_obj.py X263b09a 1 /app/work/X263b09a/search_1/best.xml --scale > /app/work/X263b09a/refine_1.log 2>&1
SEARCH_TIME=2200 MC_STEPS=4000000 TARGET_RW=.12 python /app/work/search_obj.py X14a2b08 1 1 --rescale --profile > /app/work/X14a2b08/search1.log 2>&1
python /app/work/refine_obj.py X14a2b08 1 /app/work/X14a2b08/search_1/best.xml --scale > /app/work/X14a2b08/refine_1.log 2>&1
