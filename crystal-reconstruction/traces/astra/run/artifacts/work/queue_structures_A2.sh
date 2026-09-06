export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/4659/status ]] && ! grep -q '^State:.*Z' /proc/4659/status; do sleep 5; done
SEARCH_TIME=2000 MC_STEPS=3000000 TARGET_RW=.09 python /app/work/search_obj.py X35b7fbc 2 1 --rescale --model=/app/work/X35b7fbc/cis.json > /app/work/X35b7fbc/search2.log 2>&1
python /app/work/refine_obj.py X35b7fbc 2 /app/work/X35b7fbc/search_2/best.xml --scale --tight > /app/work/X35b7fbc/refine_2.log 2>&1
SEARCH_TIME=1600 MC_STEPS=3000000 TARGET_RW=.07 python /app/work/search_obj.py Xbfeeda9 1 1 --rescale --bump > /app/work/Xbfeeda9/search1.log 2>&1
python /app/work/refine_obj.py Xbfeeda9 1 /app/work/Xbfeeda9/search_1/best.xml --scale --tight > /app/work/Xbfeeda9/refine_1.log 2>&1
SEARCH_TIME=1400 MC_STEPS=3000000 TARGET_RW=.07 python /app/work/search_obj.py X4f6fe58 3 2 --rescale --fullbump --profile > /app/work/X4f6fe58/search3.log 2>&1
python /app/work/refine_obj.py X4f6fe58 3 /app/work/X4f6fe58/search_3/best.xml --scale --tight --fixB > /app/work/X4f6fe58/refine_3.log 2>&1
