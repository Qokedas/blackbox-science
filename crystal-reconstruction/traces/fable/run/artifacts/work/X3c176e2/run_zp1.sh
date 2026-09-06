#!/bin/bash
cd /app/work
for sg in "P c a m" "P c n m" "P m n m" "P c m m" "P m a m"; do
  tag=$(echo $sg | tr -d ' ')
  TTMAX=40 python inositol_scan.py "$sg" 1 0,1,2,3,4,5,8 800000 1 $tag > X3c176e2/inos_$tag.log 2>&1
done
