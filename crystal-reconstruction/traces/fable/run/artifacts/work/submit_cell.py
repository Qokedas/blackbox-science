import sys, json, gemmi, os
iid = sys.argv[1]
cell = [float(v) for v in sys.argv[2:8]]
hm = sys.argv[8]
sg = gemmi.find_spacegroup_by_name(hm)
assert sg is not None, 'unknown space group ' + hm
js = {"cell": {"a": cell[0], "b": cell[1], "c": cell[2], "alpha": cell[3], "beta": cell[4], "gamma": cell[5]},
      "space_group": sg.hm, "space_group_number": sg.number}
os.makedirs('/app/results/submission', exist_ok=True)
json.dump(js, open(f'/app/results/submission/{iid}.json', 'w'), indent=1)
print(iid, js)
