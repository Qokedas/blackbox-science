export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/8405/status ]] && ! grep -q '^State:.*Z' /proc/8405/status; do sleep 5; done
python /app/work/import_de.py Xdcc971e de11 > /app/work/Xdcc971e/import_de11.log 2>&1
python /app/work/refine_obj.py Xdcc971e de11 /app/work/Xdcc971e/search_de11/best.xml --scale > /app/work/Xdcc971e/refine_de11.log 2>&1
SEARCH_TIME=300 TRIALS=1 DE_STOL=.23 python /app/work/solve_de.py Xdcc971e de12 --model=/app/work/Xdcc971e/alltrans.json --hydrogen --seed-xml=/app/work/Xdcc971e/refined_10.xml > /app/work/Xdcc971e/de12.log 2>&1
python /app/work/import_de.py Xdcc971e de12 > /app/work/Xdcc971e/import_de12.log 2>&1
python /app/work/refine_obj.py Xdcc971e de12 /app/work/Xdcc971e/search_de12/best.xml --scale > /app/work/Xdcc971e/refine_de12.log 2>&1
