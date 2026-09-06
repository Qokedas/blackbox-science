export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_raw.json NPEAK=35 MAXITER=1200 TRIALS=30 INDEX_TIME=900 NSPUR=2 INDEX_TAG=de_ext VMIN=1050 VMAX=1500 VTARGET=1300
while [[ -r /proc/8732/status ]] && ! grep -q '^State:.*Z' /proc/8732/status; do sleep 5; done
for id in X8a06d7a X263b09a X1db5091; do
 export SELECT_FILE=/app/work/$id/peak_select_ext.json
 if [[ $id == X1db5091 ]]; then PEAK_SKIP=1 BROAD=1 python /app/work/index_de.py $id > /app/work/$id/de_ext.log 2>&1
 else python /app/work/index_de.py $id > /app/work/$id/de_ext.log 2>&1; fi
done
