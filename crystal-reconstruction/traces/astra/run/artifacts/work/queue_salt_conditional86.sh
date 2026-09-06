set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=4 HBOND_MULTIPLE=1
while [[ -r /proc/56091/status ]] && ! grep -q '^State:.*Z' /proc/56091/status;do sleep 5;done
for id in X9af54a2 X35b7fbc;do
 mkdir -p /app/work/$id/search_chem86
 cp /app/work/$id/search_g11/model.json /app/work/$id/search_chem86/model.json
 python /app/work/refine_obj.py $id chem86 /app/work/$id/refined_g11.xml --scale --tight --stol=.4 > /app/work/$id/refine_chem86.log 2>&1
 GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 86 /app/work/$id/refined_chem86.xml /app/work/$id/search_chem86/model.json > /app/work/$id/warm86.log 2>&1
 schedule='1,3;0;2;1,3;0;2'; [[ $id == X35b7fbc ]] && schedule='1;0;1;0'
 BUMP_COEFF=90 HBOND_COEFF=20 PARTICLES=128 ITERATIONS=400 FREE_SCHEDULE=$schedule python /app/work/search_conditional.py $id 86 87 > /app/work/$id/conditional87.log 2>&1
 python /app/work/import_gallop.py $id 87 > /app/work/$id/import_g87.log 2>&1
 python /app/work/refine_obj.py $id g87 /app/work/$id/search_g87/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g87.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_g87.cif --check > /app/work/$id/check_g87.log 2>&1
 python /app/work/check_stereo.py $id /app/work/$id/refined_g87.cif >> /app/work/$id/check_g87.log 2>&1
done
