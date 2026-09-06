# Scores

Frozen verifier output, copied from `traces/<model>/verifier/score_breakdown.json`. Unit L = cell and space-group type (1 point). Unit S = full non-hydrogen structure (2 points). Score = points / 90.

| model | score | points | L passes | S passes | wall clock |
|---|---:|---:|---:|---:|---|
| Fable 5.1 | 0.211111 | 19/90 | 13 | 3 | 7.25 h (stopped itself) |
| GPT-6 Astra | 0.477778 | 43/90 | 23 | 10 | 8.00 h (deadline) |

## Per instance

| id | compound | data | DoF | Fable L | Fable S | Fable S reason | Astra L | Astra S | Astra S reason |
|---|---|---|---:|:-:|:-:|---|:-:|:-:|---|
| X019b9a4 | Pigment Yellow 181 Dimethylsulfoxide <i>N</i>-methyl-2-Pyrro | lab_Cu | 26 | · | · | no CIF submitted | ✓ | ✗ | no periodic mapping within matcher tolerance |
| X07806d9 | 5-Aminolevulinic acid hydrochloride | synchrotron | 13 | ✓ | ✓ | rmsd 0.06 Å | ✓ | ✓ | rmsd 0.05 Å |
| X13023e3 | <i>S</i>-Ibuprofen--nicotinamide | synchrotron | 17 | · | · | no CIF submitted | ✓ | ✓ | rmsd 0.15 Å |
| X14a2b08 | ACM-CPR | lab_Cu | 18 | · | · | no CIF submitted | ✓ | ✗ | displacements exceed tolerance |
| X1a56c78 | Trihexyphenidyl hydrochloride | lab_Cu | 14 | · | · | no CIF submitted | ✓ | ✗ | displacements exceed tolerance |
| X1db5091 | ACEMETACINNICOTINAMIDEFORMI | lab_Cu | 19 | · | · | no CIF submitted | ✓ | ✗ | no periodic mapping within matcher tolerance |
| X2327841 | (<i>S</i>)-9-methyltriacontane | synchrotron | 34 | ✓ | · | no CIF submitted | ✓ | ✓ | rmsd 0.14 Å |
| X238783d | Clarithromycin | lab_Cu | 14 | ✓ | · | no CIF submitted | ✓ | ✗ | no periodic mapping within matcher tolerance |
| X263b09a | ACEMETACINVLM | lab_Cu | 18 | · | · | no CIF submitted | ✓ | ✗ | displacements exceed tolerance |
| X35b7fbc | methylergometrine maleate | synchrotron | 18 | ✓ | ✗ | displacements exceed tolerance | ✓ | ✗ | displacements exceed tolerance |
| X3c176e2 | cis-inositol | lab_Cu | 12 | ✓ | · | no CIF submitted | ✓ | ✓ | rmsd 0.06 Å |
| X3f4781b | Clopidogrel hydrogen sulfate | lab_Cu | 30 | ✓ | · | no CIF submitted | ✓ | ✗ | no periodic mapping within matcher tolerance |
| X4f6fe58 | Phenazepam, \b-polymorph | lab_Cu | 7 | · | · | no CIF submitted | ✗ | ✗ | no periodic mapping within matcher tolerance |
| X7e382cb | Diammonium 4,4'-biphenyldicarboxylate | lab_Mo | 15 | · | · | no CIF submitted | ✗ | ✗ | atom count 40 vs reference 20 after primitive reduction |
| X8a06d7a | Acemetacin cocrystals and salts: structure solution from pow | lab_Cu | 19 | · | · | no CIF submitted | ✗ | ✗ | displacements exceed tolerance |
| X8a6f5a8 | Carvedilol dihydrogen phosphate isopropanol solvate | lab_Cu | 28 | · | · | no CIF submitted | ✗ | · | no CIF submitted |
| X9af54a2 | Midodrine hydrochloride Form A | synchrotron | 15 | ✓ | ✓ | rmsd 0.11 Å | ✗ | ✗ | no periodic mapping within matcher tolerance |
| Xb7088cf | entinostat Form B | lab_Mo | 12 | · | · | no CIF submitted | ✗ | ✗ | no periodic mapping within matcher tolerance |
| Xbfc6d2c | 4,4'-Diisocyano-3,3'-dimethylbiphenyl | lab_Cu | 7 | · | · | no CIF submitted | ✓ | ✓ | rmsd 0.08 Å |
| Xbfeeda9 | loperamide hydrochloride anhydrate | lab_Cu | 16 | · | · | no CIF submitted | ✓ | ✓ | rmsd 0.17 Å |
| Xd4c1a35 | Griseofulvin | synchrotron | 18 | ✓ | · | no CIF submitted | ✓ | ✓ | rmsd 0.07 Å |
| Xd8634a2 | \ 3-{[3-Fluoro-2-(methylsulfamoylamino)pyridin-4-yl]methyl}- | synchrotron | 13 | ✓ | ✓ | rmsd 0.13 Å | ✓ | ✗ | displacements exceed tolerance |
| Xdcc971e | (<i>S</i>)-13-methylnonacosane | synchrotron | 32 | ✓ | · | no CIF submitted | ✓ | ✗ | displacements exceed tolerance |
| Xe1fb77b | cynarine monohydrate | synchrotron | 16 | ✓ | · | no CIF submitted | ✓ | ✗ | no periodic mapping within matcher tolerance |
| Xe3a2935 | Levosimendan | synchrotron | 9 | ✓ | ✗ | displacements exceed tolerance | ✓ | ✓ | rmsd 0.09 Å |
| Xeb393f9 | 1-(3-Carboxypropyl)-4-[(4-chlorophenyl)(pyridin-2-yl)methoxy | synchrotron | 21 | · | · | no CIF submitted | ✓ | ✗ | displacements exceed tolerance |
| Xebbd488 | Carvedilol dihydrogen phosphate hemihydrate | lab_Cu | 23 | · | · | no CIF submitted | ✗ | · | no CIF submitted |
| Xedd9c7b | psilocybin Form B | lab_Cu | 22 | · | · | no CIF submitted | ✓ | ✗ | displacements exceed tolerance |
| Xf8ac963 | (1<i>R</i>,2<i>S</i>,5<i>R</i>)-Acoltremon | synchrotron | 10 | ✓ | ✗ | mirror image of a chiral structure | ✓ | ✓ | rmsd 0.11 Å |
| Xfca9f3c | (<i>S</i>)-9-methylpentacosane | synchrotron | 28 | · | · | no CIF submitted | ✓ | ✓ | rmsd 0.11 Å |

✓ pass · ✗ submitted and failed · · not submitted. Reasons are the grader's own strings.
