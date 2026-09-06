export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python /app/work/enumerate_methoxy.py Xd4c1a35 /app/work/Xd4c1a35/refined_2freeh.xml /app/work/Xd4c1a35/search_2freeh/model.json methoxy > /app/work/Xd4c1a35/methoxy.log 2>&1
python /app/work/refine_obj.py Xd4c1a35 methoxy /app/work/Xd4c1a35/search_methoxy/best.xml --scale --tight > /app/work/Xd4c1a35/refine_methoxy.log 2>&1
