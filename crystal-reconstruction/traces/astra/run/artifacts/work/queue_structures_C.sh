export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/3401/status ]] && ! grep -q '^State:.*Z' /proc/3401/status; do sleep 5; done
SEARCH_TIME=1200 MC_STEPS=2000000 TARGET_RW=.1 python /app/work/search_obj.py X13023e3 2 1 --rescale --lsq > /app/work/X13023e3/search2.log 2>&1
python /app/work/refine_obj.py X13023e3 2 /app/work/X13023e3/search_2/best.xml --scale > /app/work/X13023e3/refine_2.log 2>&1
SEARCH_TIME=1600 MC_STEPS=3000000 TARGET_RW=.09 python /app/work/search_obj.py Xd4c1a35 1 2 --rescale --lsq > /app/work/Xd4c1a35/search1.log 2>&1
python /app/work/refine_obj.py Xd4c1a35 1 /app/work/Xd4c1a35/search_1/best.xml --scale > /app/work/Xd4c1a35/refine_1.log 2>&1
