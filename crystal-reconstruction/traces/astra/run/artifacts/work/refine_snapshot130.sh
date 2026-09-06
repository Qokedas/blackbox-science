export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python /app/work/import_gallop.py X13023e3 41 > /app/work/X13023e3/import_g41.log 2>&1
python /app/work/refine_obj.py X13023e3 g41 /app/work/X13023e3/search_g41/best.xml --scale --tight > /app/work/X13023e3/refine_g41.log 2>&1
