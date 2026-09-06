set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X263b09a
GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 72 /app/work/$id/search_synseed72/best.xml /app/work/$id/search_synseed72/model.json > /app/work/$id/warm72.log 2>&1
SEARCH_TIME=1500 PARTICLES=128 ITERATIONS=450 HBOND_COEFF=10 BUMP_COEFF=60 START_NPZ=/app/work/$id/gallop_72/warm.npz START_JITTER=.10 START_TOR_JITTER=.4 MACRO_ELITE_FRAC=.35 python /app/work/search_gallop.py $id 72 1 --hscatter --packing > /app/work/$id/gallop72.log 2>&1
python /app/work/import_gallop.py $id 72 > /app/work/$id/import_g72.log 2>&1
python /app/work/refine_obj.py $id g72 /app/work/$id/search_g72/best.xml --scale --tight --stol=.38 > /app/work/$id/refine_g72.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g72.cif --check > /app/work/$id/check_g72.log 2>&1
id=X14a2b08
GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 72 /app/work/$id/search_transfer72/best.xml /app/work/$id/search_transfer72/model.json > /app/work/$id/warm72.log 2>&1
SEARCH_TIME=1500 PARTICLES=128 ITERATIONS=450 HBOND_COEFF=12 BUMP_COEFF=60 START_NPZ=/app/work/$id/gallop_72/warm.npz START_JITTER=.10 START_TOR_JITTER=.4 MACRO_ELITE_FRAC=.35 python /app/work/search_gallop.py $id 72 1 --hscatter --packing > /app/work/$id/gallop72.log 2>&1
python /app/work/import_gallop.py $id 72 > /app/work/$id/import_g72.log 2>&1
python /app/work/refine_obj.py $id g72 /app/work/$id/search_g72/best.xml --scale --tight --stol=.38 > /app/work/$id/refine_g72.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g72.cif --check > /app/work/$id/check_g72.log 2>&1
