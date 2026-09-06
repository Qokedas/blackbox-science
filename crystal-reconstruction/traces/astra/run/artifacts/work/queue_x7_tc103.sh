set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CHARGED_N_MIN=3.15 CHARGED_NO_MIN=2.65 ACCEPTOR_NO_MIN=2.80
id=X7e382cb
python /app/work/import_graph_cif.py $id /app/work/$id/tc2/best.cif p1tc103 > /app/work/$id/import_tc103.log 2>&1
python /app/work/submit.py $id /app/work/$id/search_p1tc103/best.cif --check > /app/work/$id/check_tc103seed.log 2>&1
python /app/work/add_ammonium_h.py $id p1tc103 ionHtc103 /app/work/$id/search_p1tc103/best.xml > /app/work/$id/addHtc103.log 2>&1
PACKING_SIGMA=.008 python /app/work/refine_obj.py $id ionHtc103 /app/work/$id/search_ionHtc103/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_ionHtc103.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_ionHtc103.cif --check > /app/work/$id/check_ionHtc103.log 2>&1
