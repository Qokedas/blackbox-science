export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for x in 'X13023e3 g12' 'Xd4c1a35 2'; do
 set -- $x;id=$1;from=$2;run=${from}stable
 mkdir -p /app/work/$id/search_$run; cp /app/work/$id/search_$from/model.json /app/work/$id/search_$run/model.json
 python /app/work/refine_stable.py $id $run /app/work/$id/search_$from/best.xml --scale --tight > /app/work/$id/refine_$run.log 2>&1
done
