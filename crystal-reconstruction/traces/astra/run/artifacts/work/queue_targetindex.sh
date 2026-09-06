export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for i in 0 1 2 3 4 5 6; do CANDIDATE_FILE=/app/work/Xedd9c7b/candidates_zero_mono.json CANDIDATE_INDEX=$i python /app/work/fit_candidate.py Xedd9c7b zero$i .3 > /app/work/Xedd9c7b/fit_zero$i.log 2>&1; done
VMIN=1100 VMAX=7800 VTARGET=2800 PLANE_ERR=.045 INDEX_TAG=axis0 python /app/work/complete_mono_axis.py X8a6f5a8 0 > /app/work/X8a6f5a8/complete_axis0.log 2>&1
VMIN=4000 VMAX=6200 VTARGET=5000 NANCHOR=9 NBANCHOR=16 TTHERR=.04 timeout 300 python /app/work/index_axial.py Xebbd488 'C 1 2 1' > /app/work/Xebbd488/axial5.log 2>&1
