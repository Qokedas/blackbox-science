export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for spec in 'Xeb393f9 1' 'Xbfc6d2c freeh' 'Xe3a2935 freeh' 'Xf8ac963 freeh' 'Xd4c1a35 2freeh'; do
 set -- $spec; id=$1; old=$2
 mkdir -p /app/work/$id/search_plan
 cp /app/work/$id/search_$old/model.json /app/work/$id/search_plan/model.json
 python /app/work/refine_obj.py $id plan /app/work/$id/refined_$old.xml --scale --tight > /app/work/$id/refine_plan.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_plan.cif --check > /app/work/$id/check_plan.log 2>&1
 python /app/work/check_stereo.py $id /app/work/$id/refined_plan.cif >> /app/work/$id/check_plan.log 2>&1
 python /app/work/contacts.py /app/work/$id/refined_plan.cif >> /app/work/$id/check_plan.log 2>&1
 done
