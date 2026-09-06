set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15 CHARGED_NO_MIN=2.65 ACCEPTOR_NO_MIN=2.80 CELL_REL_LIMIT=.004 CELL_ANGLE_LIMIT=.25
id=X7e382cb
mkdir -p /app/work/$id/search_bound108
cp /app/work/$id/search_ionHcross107/model.json /app/work/$id/search_bound108/model.json
PACKING_SIGMA=.008 python /app/work/refine_obj.py $id bound108 /app/work/$id/refined_ionHcross107.xml --scale --tight --stol=.4 > /app/work/$id/refine_bound108.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_bound108.cif --check > /app/work/$id/check_bound108.log 2>&1
