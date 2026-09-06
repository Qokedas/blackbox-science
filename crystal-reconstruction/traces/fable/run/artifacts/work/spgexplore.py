import sys, json, numpy as np, time, os
sys.path.insert(0, '/app/work')
from lebail import *

def explore(iid, cell, ttmax=None, fitprofile_all=False, nbest=15, verbose=False):
    p, ins = make_pattern(iid, tt_max=ttmax)
    cr, pd = add_crystal(p, cell, 'P1')
    pd.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 1e-7)
    steps = [['Zero'], ['W'], ['a', 'b', 'c', 'alpha', 'beta', 'gamma'], ['U', 'V'], ['Eta0'], ['Eta1'], ['background'],
             ['Zero', 'W', 'U', 'V', 'Eta0', 'background', 'a', 'b', 'c', 'alpha', 'beta', 'gamma']]
    lsq = fit_sequence(p, pd, steps, verbose=verbose)
    print(f'P1 LeBail Rwp={p.GetRw():.4f} chi2={p.GetChi2():.1f}', flush=True)
    ex = SpaceGroupExplorer(pd)
    ex.RunAll(fitprofile_all, verbose, True, False, True)
    scores = ex.GetScores()
    out = []
    for s in scores:
        out.append((s.hermann_mauguin, s.Rw, s.GoF, s.nGoF))
    return out, p, cr, pd

if __name__ == '__main__':
    iid = sys.argv[1]
    cell = [float(v) for v in sys.argv[2:8]]
    ttmax = float(sys.argv[8]) if len(sys.argv) > 8 else None
    t0 = time.time()
    out, p, cr, pd = explore(iid, cell, ttmax=ttmax)
    nheavy = {x['id']: x['heavy_atoms_per_formula_unit'] for x in json.load(open('/app/data/instances.json'))['instances']}[iid]
    V = cr.GetVolume()
    print(f'{iid} cell={cell} V={V:.1f} V/18/nheavy={V/18/nheavy:.2f}  t={time.time()-t0:.0f}s')
    print(' HM                  Rwp     GoF    nGoF')
    with open(f'/app/work/{iid}/spgexplore.txt', 'a') as f:
        f.write(f'# cell={cell} V={V:.1f}\n')
        for hm, rw, gof, ngof in out[:40]:
            line = f'{hm:18s} {rw:8.4f} {gof:10.2f} {ngof:10.2f}'
            print(line); f.write(line+'\n')
    os._exit(0)
