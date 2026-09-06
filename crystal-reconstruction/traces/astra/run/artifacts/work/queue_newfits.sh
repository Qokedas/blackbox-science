export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
CANDIDATE_FILE=/app/work/Xebbd488/index_axial_5.json CANDIDATE_INDEX=0 python /app/work/fit_candidate.py Xebbd488 axial5 .33 > /app/work/Xebbd488/fit_axial5.log 2>&1
for i in 0 3 7; do CANDIDATE_FILE=/app/work/X8a6f5a8/index_axis0.json CANDIDATE_INDEX=$i python /app/work/fit_candidate.py X8a6f5a8 axis$i .33 > /app/work/X8a6f5a8/fit_axis$i.log 2>&1; done
MAX_STOL=.23 python /app/work/create_stable_base.py Xedd9c7b zero0 'P 1 21/a 1' --submit > /app/work/Xedd9c7b/basefresh.log 2>&1
