set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X14a2b08
python /app/work/transfer_acm.py X263b09a $id g91 transfer73 > /app/work/$id/transfer73.log 2>&1
GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 73 /app/work/$id/search_transfer73/best.xml /app/work/$id/search_transfer73/model.json > /app/work/$id/warm73.log 2>&1
SEARCH_TIME=1500 PARTICLES=128 ITERATIONS=450 HBOND_COEFF=12 BUMP_COEFF=60 START_NPZ=/app/work/$id/gallop_73/warm.npz START_JITTER=.10 START_TOR_JITTER=.4 MACRO_ELITE_FRAC=.4 python /app/work/search_gallop.py $id 73 1 --hscatter --packing > /app/work/$id/gallop73.log 2>&1
python /app/work/import_gallop.py $id 73 > /app/work/$id/import_g73.log 2>&1
python /app/work/refine_obj.py $id g73 /app/work/$id/search_g73/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g73.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g73.cif --check > /app/work/$id/check_g73.log 2>&1
