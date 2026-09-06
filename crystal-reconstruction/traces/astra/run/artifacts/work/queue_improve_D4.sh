export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/9939/status ]] && ! grep -q '^State:.*Z' /proc/9939/status; do sleep 5; done
for id in X07806d9 Xbfc6d2c Xe3a2935 Xf8ac963 X3c176e2; do
 tag=1h; [[ $id == X3c176e2 ]] && tag=10h
 mkdir -p /app/work/$id/search_freeh
 cp /app/work/$id/search_${tag}/model.json /app/work/$id/search_freeh/model.json
 python /app/work/refine_obj.py $id freeh /app/work/$id/refined_${tag}.xml --scale --tight > /app/work/$id/refine_freeh.log 2>&1
done
cp -r /app/work/X13023e3/gallop_11 /app/work/X13023e3/gallop_31
rm -f /app/work/X13023e3/gallop_31/STOP
SEARCH_TIME=2200 PARTICLES=128 ITERATIONS=400 START_NPZ=/app/work/X13023e3/gallop_11/best.npz START_JITTER=.20 START_TOR_JITTER=.6 python /app/work/search_gallop.py X13023e3 31 1 --packing --hscatter > /app/work/X13023e3/gallop31.log 2>&1
python /app/work/import_gallop.py X13023e3 31 > /app/work/X13023e3/import_g31.log 2>&1
python /app/work/refine_obj.py X13023e3 g31 /app/work/X13023e3/search_g31/best.xml --scale --tight > /app/work/X13023e3/refine_g31.log 2>&1
SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.24 CONF_RANK=0 python /app/work/search_gallop.py X1a56c78 11 1 --prepare --hscatter > /app/work/X1a56c78/gallop11.log 2>&1
python /app/work/import_gallop.py X1a56c78 11 > /app/work/X1a56c78/import_g11.log 2>&1
python /app/work/refine_obj.py X1a56c78 g11 /app/work/X1a56c78/search_g11/best.xml --scale --tight > /app/work/X1a56c78/refine_g11.log 2>&1
SEARCH_TIME=2200 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.24 CONF_RANK=0 python /app/work/search_gallop.py X8a06d7a 11 1 --prepare --hscatter > /app/work/X8a06d7a/gallop11.log 2>&1
python /app/work/import_gallop.py X8a06d7a 11 > /app/work/X8a06d7a/import_g11.log 2>&1
python /app/work/refine_obj.py X8a06d7a g11 /app/work/X8a06d7a/search_g11/best.xml --scale --tight > /app/work/X8a06d7a/refine_g11.log 2>&1
