export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
mkdir -p /app/work/Xeb393f9/search_chem50
cp /app/work/Xeb393f9/search_g50/model.json /app/work/Xeb393f9/search_chem50/model.json
PACKING_SIGMA=.01 python /app/work/refine_obj.py Xeb393f9 chem50 /app/work/Xeb393f9/refined_g50.xml --scale --tight --packing --stol=.40 > /app/work/Xeb393f9/refine_chem50.log 2>&1
python /app/work/submit.py Xeb393f9 /app/work/Xeb393f9/refined_chem50.cif --check > /app/work/Xeb393f9/check_chem50.log 2>&1
python /app/work/check_stereo.py Xeb393f9 /app/work/Xeb393f9/refined_chem50.cif >> /app/work/Xeb393f9/check_chem50.log 2>&1
