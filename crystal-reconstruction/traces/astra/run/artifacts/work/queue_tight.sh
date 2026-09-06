export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
# Retain a physical model for the promising nicotinamide/ibuprofen trial.
mkdir -p /app/work/X13023e3/search_g12t; cp /app/work/X13023e3/search_g12/model.json /app/work/X13023e3/search_g12t/model.json
python /app/work/refine_obj.py X13023e3 g12t /app/work/X13023e3/search_g12/best.xml --scale --tight > /app/work/X13023e3/refine_g12t.log 2>&1
for id in Xfca9f3c Xdcc971e X2327841; do
 mkdir -p /app/work/$id/search_10t; cp /app/work/$id/search_10/model.json /app/work/$id/search_10t/model.json
 if [[ $id == X2327841 ]]; then src=/app/work/$id/refined_10.xml;else src=/app/work/$id/refined_10h.xml; fi
 python /app/work/refine_obj.py $id 10t $src --scale --tight --stol=.38 > /app/work/$id/refine_10t.log 2>&1
done
