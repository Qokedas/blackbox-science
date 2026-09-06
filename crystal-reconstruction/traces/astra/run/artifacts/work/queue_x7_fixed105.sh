set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15 CHARGED_NO_MIN=2.65 ACCEPTOR_NO_MIN=2.80
id=X7e382cb
python /app/work/reset_cell_seed.py $id /app/work/$id/refined_ionH101.xml /app/work/$id/search_ionH101/model.json /app/work/$id/submission_before_fallback.json fixed105 > /app/work/$id/reset105.log 2>&1
PACKING_SIGMA=.008 python /app/work/refine_obj.py $id fixed105 /app/work/$id/search_fixed105/best.xml --scale --tight --stol=.4 --fix-cell > /app/work/$id/refine_fixed105.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_fixed105.cif --check > /app/work/$id/check_fixed105.log 2>&1
