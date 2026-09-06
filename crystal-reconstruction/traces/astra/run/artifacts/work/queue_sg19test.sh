set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X1a56c78
python /app/work/sg_transfer_scan.py $id /app/work/$id/refined_chair84m00.xml /app/work/$id/search_chair84m00/model.json 'P 21 21 21' sg19test99 > /app/work/$id/sg19test99.log 2>&1
python /app/work/refine_obj.py $id sg19test99 /app/work/$id/search_sg19test99/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_sg19test99.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_sg19test99.cif --check > /app/work/$id/check_sg19test99.log 2>&1
python /app/work/check_stereo.py $id /app/work/$id/refined_sg19test99.cif >> /app/work/$id/check_sg19test99.log 2>&1
