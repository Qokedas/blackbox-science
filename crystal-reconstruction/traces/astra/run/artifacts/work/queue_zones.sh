export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NPEAK=25 NLOW=14 NEED=10 TTHERR=.035
while [[ -r /proc/14544/status ]] && ! grep -q '^State:.*Z' /proc/14544/status; do sleep 2;done
for id in X8a6f5a8 Xebbd488 Xedd9c7b; do timeout 240 nice -n 10 python /app/work/find_zones.py $id > /app/work/$id/find_zones.log 2>&1;done
