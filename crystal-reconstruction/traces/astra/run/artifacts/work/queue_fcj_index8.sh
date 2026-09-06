set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python /app/work/fcj_refine_cells.py > /app/work/X8a6f5a8/fcj_refine_cells.log 2>&1
export PEAK_FILE=peaks_fcj.json SELECT_FILE=/app/work/X8a6f5a8/peak_select_fcj.json NPEAK=23 NSPUR=1 TTHERR=.015 TRIALS=120 INDEX_TIME=450 VTARGET=1500 AMAX=45 ZEROMAX=.08
VMIN=1000 VMAX=2100 SG_FILTER='P 1 21 1' INDEX_TAG=fcj4z2 python /app/work/index_metric.py X8a6f5a8 MONOCLINIC P > /app/work/X8a6f5a8/index_fcj4z2.log 2>&1
VMIN=2100 VMAX=3800 SG_FILTER='P 1 21 1' INDEX_TAG=fcj4z4 python /app/work/index_metric.py X8a6f5a8 MONOCLINIC P > /app/work/X8a6f5a8/index_fcj4z4.log 2>&1
VMIN=2000 VMAX=4100 SG_FILTER='P 21 21 21' INDEX_TAG=fcj19 python /app/work/index_metric.py X8a6f5a8 ORTHOROMBIC P > /app/work/X8a6f5a8/index_fcj19.log 2>&1
