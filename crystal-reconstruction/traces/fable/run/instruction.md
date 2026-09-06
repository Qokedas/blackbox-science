# Blind crystal-structure solution from laboratory powder X-ray diffraction

You are the solid-state crystallographer. For each of the samples in `/app/data/instances/`, a crystalline organic solid form (a molecular compound, salt, hydrate, solvate or co-crystal) would not give single crystals, so only a powder X-ray diffraction pattern was measured. You know exactly what was in the sample (the components with their stoichiometry, as SMILES). You do not know the unit cell, the space group, how many formula units are in the cell, or where any atom is. Your job is to determine the crystal structure that produced each pattern and submit it as a CIF, together with a small JSON stating the cell and space group.

This is the complete, unassisted structure-determination job: background and peak positions, indexing and choice among candidate cells, space-group determination from systematic absences and the volume-per-atom rule, intensity extraction (Pawley or Le Bail), model building (conformers, protonation, number of independent fragments), direct-space global optimisation against the pattern, judging convergence against false minima, restrained Rietveld refinement, and writing a valid CIF. All of it happens inside this container; there is no network.

## Inputs

`/app/data/instances.json` lists the instance ids. For each `<id>`:

- `pattern.xye`: three columns, `two_theta_deg intensity sigma`, the observed powder pattern as deposited by the original experimenters. Only observed data: no calculated profile, no background curve, no reflection list. For a few patterns the depositors deposited the instrument-background-subtracted net intensity; `instrument.json` says which column you have.
- `instrument.json`: radiation (wavelength(s) in Å, Kα1 or Kα1/Kα2 with weights where given, monochromator, source type), geometry (transmission capillary / reflection flat plate, where stated), temperature (K), 2θ range and point count, and what the intensity and sigma columns are. Everything needed for a profile model; nothing about the structure.
- `composition.json`: the components of one formula unit as SMILES with counts and charges, exactly as the chemist knew them. Stereodescriptors are present only when the compound is chiral; keep that stereochemistry. Hydrogen positions and protonation sites are not assessed, so the SMILES protonation state is information, not a constraint on your model beyond the heavy-atom connectivity.

Read `/app/TOOLS.md` for the installed software (pymatgen, spglib, gemmi, RDKit, xtb, pyobjcryst/ObjCryst++ (the FOX engine, including its indexing module), GALLOP on CPU, GSAS-II scriptable, gfortran/gcc). You have 4 CPU cores, no GPU and eight hours of wall clock for the whole panel, including everything you compute and every message you write. Budget deliberately: not every instance is equally hard, and an indexed cell with the right space group is worth submitting even when the structure did not converge.

## What to submit

Write, for every instance you attempt, exactly two files under `/app/results/submission/`:

1. `/app/results/submission/<id>.json`
```json
{"cell": {"a": 16.7095, "b": 12.3773, "c": 13.2135, "alpha": 90.0, "beta": 101.642, "gamma": 90.0},
 "space_group": "P 21/c",
 "space_group_number": 14}
```
Lengths in Å, angles in degrees, for the cell in which the space-group symbol is expressed (any setting is fine, e.g. `P 21/n` with its own β; centred cells are fine when the symbol carries the centring letter). `space_group_number` is optional; if given it must agree with the symbol.

2. `/app/results/submission/<id>.cif`: one data block containing the same cell, the space group (H-M symbol and, ideally, the list of symmetry operations `_space_group_symop_operation_xyz`), and the atom sites of the asymmetric unit with element symbols and fractional coordinates. All non-hydrogen atoms of the asymmetric unit must be present, each as a single, fully occupied site. Hydrogen atoms are optional and ignored. The CIF must be readable by a standard parser (pymatgen `CifParser` is what the evaluator uses; gemmi is a good writer).

One structure per instance. If an instance has more than one CIF (for example `<id>.cif` and `<id>_alt.cif`) or a CIF with more than one data block, that instance scores zero: hedging buys nothing. An instance with a JSON but no CIF can still earn the cell-and-symmetry unit. Instances with no files earn nothing. Partial panels are fine; there is no penalty for leaving an instance out other than the points it would have earned. Notes to yourself go under `/app/work/`, not under `/app/results/`.

## How it is scored

Two independent binary units per instance, judged against the deposited crystal structure of the same phase, which you do not have. Points: 1 for the lattice-and-symmetry unit, 2 for the structure unit; the benchmark score is total points divided by 3 × (number of instances).

**Unit L, lattice and symmetry (1 point).** Your cell (from the JSON, or from the CIF if the JSON is missing) is reduced to its primitive Niggli form and compared with the reference's: the two lattices must map onto each other with all lengths within 1 % and all angles within 1°, and your space-group type must be the reference's type (any setting or origin choice; enantiomorphic pairs such as P4₁/P4₃ count as the same type). Sub-cells, super-cells, a wrong crystal system, or the right lattice described in a lower-symmetry group all fail this unit.

**Unit S, structure (2 points).** Your CIF is expanded with its own symmetry, hydrogens are dropped, and heavy-atom bonds are perceived from interatomic distances. The perceived molecules must match the supplied components and stoichiometry (same heavy-atom connectivity graphs, counts in the cell in the given ratio); a set of atoms with a good profile fit but the wrong connectivity is not a structure and fails. Then both structures are reduced to primitive cells and matched as periodic arrangements (symmetry-aware, any origin, any setting). S passes when the root-mean-square displacement over all non-hydrogen atoms in the cell is ≤ 0.35 Å and no single atom is displaced by more than 1.0 Å, measured in the reference lattice frame. A flipped ring, a swapped N/O, a rotated substituent, or a molecule in the wrong orientation fails. For achiral components crystallising in a Sohncke space group either hand is accepted (powder data cannot distinguish them); for chiral components the supplied stereochemistry must be present in your model.

S can pass while L fails (a correct arrangement described in P1 or in a subgroup is still the correct arrangement) and L can pass while S fails (indexed, not solved). Nothing is awarded for closeness: a structure with RMSD 0.5 Å earns the same as an empty submission on that unit.

## Working notes from the profession

- Index carefully. Several cells with comparable figures of merit will often fit the first twenty lines; check them against the volume expected from the composition (about 18 Å³ per non-hydrogen atom for organics at room temperature, a little less for salts and halogenated compounds), against Z consistent with a plausible space group, and by a Pawley or Le Bail fit of the whole pattern. Zero-point and sample-displacement errors shift low-angle lines. Kα1/Kα2 doublets, when present, must be modelled or the second component removed before peak picking.
- Extinction symbols decide between candidate space groups; when they do not, the density and the number of independent molecules do, and only a full solution attempt settles the rest. Centrosymmetric groups P2₁/c, P-1, Pbca, C2/c and the chiral P2₁, P2₁2₁2₁, C2 dominate organic molecular crystals; enantiopure compounds cannot be in centrosymmetric groups.
- Build the model from the SMILES: rigid units plus flexible torsions, sensible protonation, one fragment per independent component (ions and solvent are separate rigid bodies). Ring conformations and hydrogen-bond-driven geometries matter. Consider Z′ > 1 when the cell volume demands it.
- Direct-space searches succeed in a fraction of runs that falls quickly above about 15 torsional and positional degrees of freedom; run several independent starts, compare the best χ² or R_wp values across runs, look at the difference plot, and check that the packing has no impossible contacts. A low profile residual is necessary but not sufficient.
- Refine with restraints and check that the final geometry is chemically reasonable before writing the CIF. Write the cell that goes with the symbol you chose.
- Time is the constraint. A cell and space group you trust are worth submitting on their own for every instance; spend the remaining hours where a solution is realistic.

When you are done, make sure `/app/results/submission/` contains the files you want graded and end your turn.
