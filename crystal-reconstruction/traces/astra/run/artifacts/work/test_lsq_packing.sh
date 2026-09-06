export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python /app/work/refine_obj.py Xeb393f9 chem0 /app/work/Xeb393f9/refined_pyrm0.xml --scale --tight --packing > /app/work/Xeb393f9/refine_chem0.log 2>&1
python /app/work/refine_obj.py X7e382cb chem32 /app/work/X7e382cb/search_g32/best.xml --scale --tight --packing > /app/work/X7e382cb/refine_chem32.log 2>&1
