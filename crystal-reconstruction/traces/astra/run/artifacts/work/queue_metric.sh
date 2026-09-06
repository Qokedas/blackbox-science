export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NPEAK=28 NSPUR=1 MAXITER=700 INDEX_TIME=350 TTHERR=.025 TRIALS=60
while [[ -r /proc/8838/status ]] && ! grep -q '^State:.*Z' /proc/8838/status; do sleep 5;done
for sys in ORTHOROMBIC MONOCLINIC; do VMIN=500 VMAX=1550 VTARGET=800 python /app/work/index_metric.py Xedd9c7b $sys P > /app/work/Xedd9c7b/metric_${sys}.log 2>&1;done
for sys in ORTHOROMBIC MONOCLINIC; do VMIN=1100 VMAX=3500 VTARGET=2200 python /app/work/index_metric.py X8a6f5a8 $sys P > /app/work/X8a6f5a8/metric_${sys}.log 2>&1;done
for sys in ORTHOROMBIC MONOCLINIC; do VMIN=1900 VMAX=3300 VTARGET=2500 python /app/work/index_metric.py Xebbd488 $sys P > /app/work/Xebbd488/metric_${sys}.log 2>&1;done
PEAK_SKIP=1 VMIN=1050 VMAX=3100 VTARGET=1600 SELECT_FILE=/app/work/X1db5091/peak_select_ext.json python /app/work/index_metric.py X1db5091 MONOCLINIC P > /app/work/X1db5091/metric_MONOCLINIC.log 2>&1
