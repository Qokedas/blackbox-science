export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_emg.json SELECT_FILE=/app/work/X8a6f5a8/peak_select_emg.json NPEAK=30 NSPUR=1 TTHERR=.018 TRIALS=120 INDEX_TIME=480 VMIN=2200 VMAX=4200 VTARGET=2800 AMAX=45 ZEROMAX=.20
SG_FILTER='P 21 21 21' INDEX_TAG=emg19 python /app/work/index_metric.py X8a6f5a8 ORTHOROMBIC P > /app/work/X8a6f5a8/index_emg19.log 2>&1
SG_FILTER='P 1 21 1' INDEX_TAG=emg4 python /app/work/index_metric.py X8a6f5a8 MONOCLINIC P > /app/work/X8a6f5a8/index_emg4.log 2>&1
HMAX=8 VMIN=1100 VMAX=3200 INDEX_TAG=emg1 python /app/work/index_metric.py X8a6f5a8 TRICLINIC P > /app/work/X8a6f5a8/index_emg1.log 2>&1
