export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/21574/status ]] && ! grep -q '^State:.*Z' /proc/21574/status; do sleep 5;done
mkdir -p /app/work/Xeb393f9/search_chem51
cp /app/work/Xeb393f9/search_g51/model.json /app/work/Xeb393f9/search_chem51/model.json
PACKING_SIGMA=.01 python /app/work/refine_obj.py Xeb393f9 chem51 /app/work/Xeb393f9/refined_g51.xml --scale --tight --packing --stol=.40 > /app/work/Xeb393f9/refine_chem51.log 2>&1
python /app/work/submit.py Xeb393f9 /app/work/Xeb393f9/refined_chem51.cif --check > /app/work/Xeb393f9/check_chem51.log 2>&1
python /app/work/check_stereo.py Xeb393f9 /app/work/Xeb393f9/refined_chem51.cif >> /app/work/Xeb393f9/check_chem51.log 2>&1
