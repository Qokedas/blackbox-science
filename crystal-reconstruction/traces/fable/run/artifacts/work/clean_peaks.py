import sys, numpy as np
# usage: clean_peaks.py <id> <tthmin> [min_snr] [exclude 2theta values...]
iid=sys.argv[1]; tthmin=float(sys.argv[2]); min_snr=float(sys.argv[3]) if len(sys.argv)>3 else 0
excl=[float(x) for x in sys.argv[4:]]
lines=open(f'/app/work/{iid}/peaks.txt').readlines()
out=[lines[0]]
n=0
for l in lines[1:]:
    if l.startswith('#'): continue
    r=[float(x) for x in l.split()]
    if r[0]<tthmin or r[4]<min_snr: continue
    if any(abs(r[0]-e)<0.01 for e in excl): continue
    out.append(l); n+=1
open(f'/app/work/{iid}/peaks_clean.txt','w').writelines(out)
print(iid,'kept',n,'of',len(lines)-1)
