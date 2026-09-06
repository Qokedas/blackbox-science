# Context-3 notes (started 04:56 UTC; hard end ~11:24 UTC)

## Fixed in this context
- polish() in solve.py now works: sets Molecule option 'Auto Optimize Starting Conformation'=No, rigid-body LSQ only
  (atom coords, cell, Zero, occupancies, Biso fixed). Test on X9af54a2: 0.1396 -> 0.1204, rms move 0.03 A.
  Xe3a2935 polish: 0.180 -> 0.1425 (but cell drifted 0.4% — cell now fixed in polish).
- RNG: ObjCryst uses libc rand(); separate processes with identical commands gave IDENTICAL results.
  Now solve.py/inositol_scan.py call ctypes.CDLL(None).srand(seed). Runs within one process (nruns>1) were always different.
- solve.py new flags: --zprime N (multiplies component counts), --conf K (K-th distinct MMFF conformer by energy).
- compare.py a.cif b.cif (pymatgen StructureMatcher), diffcif.py a b (same-label displacement).

## Status
- X9af54a2 finalized (CIF+JSON). X07806d9 done.
- Xe3a2935: P212121 conf0 runs 0/1 same structure Rwp 0.185; conf2 (methyl equatorial) run0 0.181. 102 peak underestimated 1.75x.
  Candidate CIFs in Xe3a2935/sol_a, sol_c2. Consider alt SGs P 2 21 21 / P 21 2 21.
- Xf8ac963: P212121 2 runs identical structure Rwp 0.224 (bad; several obs peaks calc=0). P 21 2 21: 0.44/1.39 (bad).
  Try P 2 21 21, P 21 21 2, P21 Z'=2 ... or leave as L-only.
- Xd8634a2: P-1, 13 DOF; first 3e6 run 0.348 (bad). Running 5e6 x2 (tags c,d).
- X3c176e2 inositol: iso map 0=cis 1=epi 2=allo 3=myo 4=neo 5=muco 6/7=chiro 8=scyllo. Pbca(P c a b) all bad (best cis 0.198).
  P212121 Z'=2 scan running (inos_p212121.log); iso0 0.221.
- X13023e3: indexing with peaks_c (SNR>=5.5, 20 peaks) monoP running (g2_monoPc.log).

## Context 4 (07:15 UTC)
- lebail.make_pattern: env EXCLUDE="lo,hi;lo,hi" (deg) inflates sigma x EXCL_FACTOR (30) in those regions and imports via
  ImportPowderPattern2ThetaObsSigma (weights=1/sigma^2 verified). Purpose: down-weight giant peaks that flatten the SA landscape.
- Xe3a2935: two pseudo-solutions A (sol_c2 run1, 0.146) and B (c2b runs, 0.148-0.149) both have calc~0 for obs reflections
  015,106,018,302,306,004,210,220,117 (reflcompare.py <id> <cif> <ttmax>) -> both probably wrong. Running x2 with 020 down-weighted.
- X3c176e2 inositol: raw-data check: 100,001,010,030,201,102 absent; 101,110,111 present; a weak peak at 27.33 = 203 (h+l odd) -> n-glide
  perp b probably violated -> keep P212121. Groups with mirrors (Pmnm, Pcam...) SA gives 0.46-0.5 (hopeless). Running P212121 Z'=2 with
  211 & 020 down-weighted (inos_p19x_a/b logs).
- Xf8ac963: 011 (3.72) and 210 (4.38) clearly present; SA in P212121 gave calc~0 for them -> false minimum. Plan: EXCLUDE="2.84,2.93;6.15,6.28".
- hbonds.py / contacts.py <cif> [dmax]: intermolecular contact listing; molgeom.py: centroid/axes.

## Context 5 (08:08 UTC)
- Xd8634a2 SOLVED: two independent 8e6-step P-1 runs (sol_e 0.126, sol_f 0.128) same structure (mean dev 0.06 A; compare.py said False
  but per-atom check with origin shift (0,0,1/2) showed identity). R(F2)=0.21. Finalized sol_e -> submission (CIF+JSON). check_structure OK.
- solve.py restore_from_cif fixed: sequential atom consumption (labels collide between molecules, e.g. cation O1/anion O1).
  X35b7fbc sol_a restored+polished -> sol_a_chk/restored_lsq_rw0.145.cif (Rwp 0.145; Le Bail 0.092; R(F2)=0.39; 063,080,073 calc~0).
  contacts.py is UNRELIABLE for multi-molecule CIFs (label collisions) -> use intercontacts.py <cif> (pymatgen; fragments + intermolecular contacts).
  sol_a_chk: closest intermolecular N...O 2.45 (short H-bond), no clashes; sol_b has cation-anion clash (fragments=4).
- Killed inositol scans (all isomers bad 0.25-0.30). X3c176e2 stays JSON only.
- Started: Xd4c1a35 (griseofulvin, chiral, P212121 Z'=2, 3e6 steps, ttmax 30) tags g1,g2 (~390 steps/s wall under load; expect finish ~10:05).
  Xf8ac963 x1 (EXCLUDE giant peaks); Xe3a2935 s2 (P 2 21 21, 2 runs).
- 08:56: X35b7fbc 'a' (sol_a_chk/restored_lsq_rw0.145.cif) FINALIZED to submission as best guess (free: wrong CIF costs nothing, L from JSON).
  a_sa2 (restore-SA) gave 0.34 -> parallel tempering randomizes anyway; --restore-sa is useless. Fresh run tag c (5e6, --maxtime 4800) running.
- Xf8ac963: raw data 030 (8.652) absent (peak at 8.643 = 303), 300/100/500 absent, 001/003 absent -> P212121 stands. EXCLUDE runs x1 0.226/0.228
  R(F2)=0.43 (bad). Running L0 (conf0) and L1 (conf1) 8e6 steps each. All low-E conformers are all-equatorial chairs.
- Xe3a2935: raw data hints 300 present (shoulder at 7.841 on 020) and 200 weak -> maybe P 2 21 21; s2 run0 gave 0.18 (worse than P212121 0.146).
  Running s3 = P 2 21 21 2x3e6.
- Plan at the end: finalize best CIF for Xf8ac963 (any), Xd4c1a35 (g1/g2 if finished), keep Xe3a2935 unless R(F2) clearly better. Run final_check.py.
- 09:55: Xf8ac963 L0/L1 (8e6 steps, independent seeds) converge to the SAME structure Rwp 0.217 (Le Bail 0.065; R(F2)=0.41; fit plot shows
  several strong obs peaks with calc~0: 011, 210, 5.77, 6.44, 7.05 deg). Reproducible false minimum -> model/SG problem unresolved.
  Finalized L0 as free CIF guess (JSON unchanged).
- Xd4c1a35 g1/g2 were IDENTICAL (same seed: ObjCryst apparently reseeds by time(NULL) at SA start; processes started 0.5 s apart).
  Result 0.42->0.258, R(F2)=0.57: bad. g3 (6e6 steps, maxtime 3600) running, ends ~10:40.
- Xe3a2935 s3 (P 2 21 21): 0.181, 0.173 -> worse than P212121 (0.146). Keep P212121 submission.
- X35b7fbc run c (5e6, maxtime 4800) ends ~10:20.
- 10:25: X35b7fbc run c (5e6): 0.202->0.167, different from 'a' (mean dev 1.5 A, some atoms coincide). 'a' (0.145) remains submitted.
  Xf8ac963 P 21 2 21 and P 21 21 2 (3e6): both 0.44 -> P212121 kept (L0 CIF submitted as guess). Xf8ac963 peak list shows only weak
  shoulders (+-0.01-0.017 deg) next to strong peaks, no unindexed peaks -> cell OK.
- Waiting for Xd4c1a35 g3 (ends ~10:40); then finalize guess CIF if parseable, final_check.py, kill all.
- 10:45 FINAL: Xd4c1a35 g3 0.377->0.287 with clashes (2.39 A C..C) -> no CIF (JSON only). All background jobs finished.
  Submission: 13 JSON (X07806d9, X2327841, X238783d, X35b7fbc, X3c176e2, X3f4781b, X9af54a2, Xd4c1a35, Xd8634a2, Xdcc971e, Xe1fb77b,
  Xe3a2935, Xf8ac963); 6 CIF (X07806d9 Pbca, X9af54a2 P21/c, Xd8634a2 P-1 [reproduced, R(F2)=0.21], X35b7fbc [best guess 0.145],
  Xe3a2935 [likely wrong], Xf8ac963 [reproducible false minimum 0.217]). final_check.py: all parse, one block each, no extra files.
