export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/4561/status ]] && ! grep -q '^State:.*Z' /proc/4561/status; do sleep 5; done
for pair in 'X3c176e2 10' 'Xe3a2935 1' 'Xf8ac963 1' 'Xbfc6d2c 1' 'X07806d9 1'; do
 set -- $pair; id=$1; run=$2; nr=${run}h
 mkdir -p /app/work/$id/search_$nr; cp /app/work/$id/search_$run/model.json /app/work/$id/search_$nr/model.json
 python /app/work/refine_obj.py $id $nr /app/work/$id/refined_$run.xml --scale --stol=.38 > /app/work/$id/refine_$nr.log 2>&1
done
