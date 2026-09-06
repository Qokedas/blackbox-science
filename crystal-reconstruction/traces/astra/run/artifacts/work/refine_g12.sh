export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python /app/work/import_gallop.py X13023e3 12 > /app/work/X13023e3/import_g12.log 2>&1
python /app/work/refine_obj.py X13023e3 g12 /app/work/X13023e3/search_g12/best.xml --scale > /app/work/X13023e3/refine_g12.log 2>&1
python /app/work/submit.py X13023e3 /app/work/X13023e3/refined_g12.cif --check > /app/work/X13023e3/check_g12.log 2>&1
