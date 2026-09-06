set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15 CHARGED_NO_MIN=2.65 ACCEPTOR_NO_MIN=2.80
id=X7e382cb
python /app/work/x7_crossover.py .5 cross107 > /app/work/$id/cross107.log 2>&1
python /app/work/add_ammonium_h.py $id cross107 ionHcross107 /app/work/$id/search_cross107/best.xml > /app/work/$id/addHcross107.log 2>&1
PACKING_SIGMA=.008 python /app/work/refine_obj.py $id ionHcross107 /app/work/$id/search_ionHcross107/best.xml --scale --tight --stol=.4 --fix-cell > /app/work/$id/refine_ionHcross107.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_ionHcross107.cif --check > /app/work/$id/check_ionHcross107.log 2>&1
