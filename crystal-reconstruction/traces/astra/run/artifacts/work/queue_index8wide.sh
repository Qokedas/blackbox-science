export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 SELECT_FILE=/app/work/X8a6f5a8/peak_select_ext2.json NPEAK=30 NSPUR=1 TTHERR=.035 TRIALS=160 INDEX_TIME=650 VMIN=2200 VMAX=7400 VTARGET=4700
while [[ -r /proc/17735/status ]] && ! grep -q '^State:.*Z' /proc/17735/status; do sleep 5; done
SG_FILTER='P 1 21 1' INDEX_TAG=wide21 python /app/work/index_metric.py X8a6f5a8 MONOCLINIC P > /app/work/X8a6f5a8/metric_wide21.log 2>&1
SG_FILTER='C 1 2 1' INDEX_TAG=wide5 python /app/work/index_metric.py X8a6f5a8 MONOCLINIC C > /app/work/X8a6f5a8/metric_wide5.log 2>&1
