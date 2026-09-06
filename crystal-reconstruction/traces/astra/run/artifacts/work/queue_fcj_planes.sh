export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/45579/status ]] && ! grep -q '^State:.*Z' /proc/45579/status;do sleep 5;done
timeout 600 python /app/work/index_plane_fcj.py > /app/work/X8a6f5a8/index_fcjplanes.log 2>&1
