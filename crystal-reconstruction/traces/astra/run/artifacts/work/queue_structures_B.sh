export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/3477/status ]] && ! grep -q '^State:.*Z' /proc/3477/status; do sleep 5; done
python /app/work/import_gallop.py Xd8634a2 2 > /app/work/Xd8634a2/import_g2.log 2>&1
python /app/work/refine_obj.py Xd8634a2 g2 /app/work/Xd8634a2/search_g2/best.xml --scale > /app/work/Xd8634a2/refine_g2.log 2>&1
for id in Xfca9f3c Xdcc971e X2327841; do
 SEARCH_TIME=500 MC_STEPS=1000000 TARGET_RW=.07 python /app/work/search_obj.py $id 10 1 --rigid --hydrogen --model=/app/work/$id/alltrans.json --rescale --lsq > /app/work/$id/alltrans_search.log 2>&1
 python /app/work/refine_obj.py $id 10 /app/work/$id/search_10/best.xml --scale > /app/work/$id/refine_10.log 2>&1
done
SEARCH_TIME=2000 MC_STEPS=3000000 TARGET_RW=.10 python /app/work/search_obj.py Xe1fb77b 2 1 --rescale --lsq --bump > /app/work/Xe1fb77b/search2.log 2>&1
python /app/work/refine_obj.py Xe1fb77b 2 /app/work/Xe1fb77b/search_2/best.xml --scale > /app/work/Xe1fb77b/refine_2.log 2>&1
