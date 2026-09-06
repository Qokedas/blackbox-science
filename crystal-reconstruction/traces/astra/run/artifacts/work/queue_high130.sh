export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ ! -f /app/work/X13023e3/refined_g31.json ]]; do sleep 5; done
mkdir -p /app/work/X13023e3/search_ghigh
cp /app/work/X13023e3/search_g31/model.json /app/work/X13023e3/search_ghigh/model.json
python /app/work/refine_obj.py X13023e3 ghigh /app/work/X13023e3/refined_g31.xml --scale --tight --stol=.40 > /app/work/X13023e3/refine_ghigh.log 2>&1
python /app/work/submit.py X13023e3 /app/work/X13023e3/refined_ghigh.cif --check > /app/work/X13023e3/check_ghigh.log 2>&1
python /app/work/check_stereo.py X13023e3 /app/work/X13023e3/refined_ghigh.cif >> /app/work/X13023e3/check_ghigh.log 2>&1
python /app/work/contacts.py /app/work/X13023e3/refined_ghigh.cif >> /app/work/X13023e3/check_ghigh.log 2>&1
