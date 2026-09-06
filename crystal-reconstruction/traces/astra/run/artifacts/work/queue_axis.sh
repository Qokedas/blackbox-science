export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/8932/status ]] && ! grep -q '^State:.*Z' /proc/8932/status; do sleep 5; done
for id in Xdcc971e X2327841; do
 if [[ $id == Xdcc971e ]]; then axis='-1,0,2';else axis='1,0,3'; fi
 SEARCH_TIME=350 TRIALS=8 DE_STOL=.23 python /app/work/solve_de.py $id deaxis --axis=$axis --model=/app/work/$id/alltrans.json --hydrogen > /app/work/$id/deaxis.log 2>&1
 python /app/work/import_de.py $id deaxis > /app/work/$id/import_deaxis.log 2>&1
 python /app/work/refine_obj.py $id deaxis /app/work/$id/search_deaxis/best.xml --scale > /app/work/$id/refine_deaxis.log 2>&1
done
