export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/2100/status ]] && ! grep -q '^State:.*Z' /proc/2100/status; do sleep 5; done
SEARCH_TIME=1000 MC_STEPS=2000000 TARGET_RW=.07 python /app/work/search_obj.py X4f6fe58 2 2 --rescale --lsq --fullbump > /app/work/X4f6fe58/search2.log 2>&1
python /app/work/refine_obj.py X4f6fe58 2 /app/work/X4f6fe58/search_2/best.xml --scale > /app/work/X4f6fe58/refine_2.log 2>&1
SEARCH_TIME=1500 MC_STEPS=2000000 TARGET_RW=.09 python /app/work/search_obj.py X35b7fbc 1 1 --rescale --lsq > /app/work/X35b7fbc/search1.log 2>&1
python /app/work/refine_obj.py X35b7fbc 1 /app/work/X35b7fbc/search_1/best.xml --scale > /app/work/X35b7fbc/refine_1.log 2>&1
SEARCH_TIME=1600 MC_STEPS=2000000 TARGET_RW=.07 python /app/work/search_obj.py Xbfeeda9 1 1 --rescale --lsq --bump > /app/work/Xbfeeda9/search1.log 2>&1
python /app/work/refine_obj.py Xbfeeda9 1 /app/work/Xbfeeda9/search_1/best.xml --scale > /app/work/Xbfeeda9/refine_1.log 2>&1
