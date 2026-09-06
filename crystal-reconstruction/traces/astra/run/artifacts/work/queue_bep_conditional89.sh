set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=4 ACCEPTOR_NO_MIN=2.80
while [[ -r /proc/54759/status ]] && ! grep -q '^State:.*Z' /proc/54759/status;do sleep 5;done
id=Xeb393f9
GALLOP_STOL=.30 python /app/work/warm_gallop.py $id 89 /app/work/$id/refined_chem51.xml /app/work/$id/search_chem51/model.json > /app/work/$id/warm89.log 2>&1
BUMP_COEFF=90 HBOND_COEFF=30 PARTICLES=128 ITERATIONS=400 FREE_SCHEDULE='1;0;1;0' python /app/work/search_conditional.py $id 89 90 > /app/work/$id/conditional90.log 2>&1
python /app/work/import_gallop.py $id 90 > /app/work/$id/import_g90.log 2>&1
python /app/work/refine_obj.py $id g90 /app/work/$id/search_g90/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g90.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g90.cif --check > /app/work/$id/check_g90.log 2>&1
python /app/work/check_stereo.py $id /app/work/$id/refined_g90.cif >> /app/work/$id/check_g90.log 2>&1
