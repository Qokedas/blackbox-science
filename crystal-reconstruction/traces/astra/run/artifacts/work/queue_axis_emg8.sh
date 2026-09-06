set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_emg.json SELECT_FILE=/app/work/X8a6f5a8/peak_select_emg.json VMIN=1800 VMAX=8500 VTARGET=2800 TTHERR=.025 NSPUR=0
PLANE_IDS=2,6,9,10,13,17,20,23 INDEX_TAG=emgaxis0 python /app/work/complete_mono_axis_emg.py X8a6f5a8 0 > /app/work/X8a6f5a8/index_emgaxis0.log 2>&1
PLANE_IDS=2,6,9,10,13,17,19,20,23 INDEX_TAG=emgaxis1 python /app/work/complete_mono_axis_emg.py X8a6f5a8 1 > /app/work/X8a6f5a8/index_emgaxis1.log 2>&1
