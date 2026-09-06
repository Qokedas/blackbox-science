export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
HALF_BASE=/app/work/X7e382cb/fit_0.xml HALF_STOL=.30 HALF_TAG=half30 TRIALS=10 SEARCH_TIME=400 python /app/work/solve_half_biphenyl.py > /app/work/X7e382cb/half30.log 2>&1
mkdir -p /app/work/Xfca9f3c/search_10h; cp /app/work/Xfca9f3c/search_10/model.json /app/work/Xfca9f3c/search_10h/model.json
python /app/work/refine_obj.py Xfca9f3c 10h /app/work/Xfca9f3c/refined_10.xml --scale --stol=.38 > /app/work/Xfca9f3c/refine_10h.log 2>&1
mkdir -p /app/work/Xdcc971e/search_10h; cp /app/work/Xdcc971e/search_10/model.json /app/work/Xdcc971e/search_10h/model.json
python /app/work/refine_obj.py Xdcc971e 10h /app/work/Xdcc971e/refined_10.xml --scale --stol=.38 > /app/work/Xdcc971e/refine_10h.log 2>&1
