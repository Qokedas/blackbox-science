export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python /app/work/enumerate_methoxy.py Xd4c1a35 /app/work/Xd4c1a35/refined_2freeh.xml /app/work/Xd4c1a35/search_2freeh/model.json methoxy2 > /app/work/Xd4c1a35/methoxy2.log 2>&1
python /app/work/refine_obj.py Xd4c1a35 methoxy2 /app/work/Xd4c1a35/search_methoxy2/best.xml --scale --tight > /app/work/Xd4c1a35/refine_methoxy2.log 2>&1
