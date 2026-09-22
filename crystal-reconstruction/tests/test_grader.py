#!/usr/bin/env python3
"""Unit tests for grade.py helpers (run: python -m pytest tests/test_grader.py -q). No benchmark data needed."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade as GR  # noqa

GR.load_deps()
Lattice = GR.Lattice


@pytest.mark.parametrize("symbol,number,expected", [
    ("P 21/c", None, 14), ("P21/c", None, 14), ("P 1 21/c 1", None, 14), ("P 1 21/n 1", None, 14), ("P2(1)/c", None, 14),
    ("P-1", None, 2), ("P -1", None, 2), ("Pbca", None, 61), ("P b c a", None, 61), ("P212121", None, 19), ("P 21 21 21", None, 19),
    ("C2/c", None, 15), ("C 1 2/c 1", None, 15), ("I2/a", None, 15), ("Pna21", None, 33), ("P n a 21", None, 33), ("P1", None, 1),
    ("Fdd2", None, 43), ("P41", None, 76), ("P43", None, 78), (None, 14, 14), ("R-3", None, 148), ("P 63/m m c", None, 194),
])
def test_parse_space_group(symbol, number, expected):
    num, cen, err = GR.parse_space_group(symbol, number)
    assert err is None, err
    assert GR.sg_type(num) == GR.sg_type(expected)


def test_space_group_conflict():
    num, cen, err = GR.parse_space_group("P 21/c", 19)
    assert num is None and err


def test_enantiomorph_merge():
    assert GR.sg_type(76) == GR.sg_type(78)
    assert GR.sg_type(212) == GR.sg_type(213)
    assert GR.sg_type(19) != GR.sg_type(18)


def test_centring_primitive_volume():
    conv = Lattice.from_parameters(10, 12, 14, 90, 100, 90)
    p = GR.primitive_lattice(conv, "C")
    assert abs(p.volume - conv.volume / 2) < 1e-6
    i = GR.primitive_lattice(conv, "I")
    assert abs(i.volume - conv.volume / 2) < 1e-6
    f = GR.primitive_lattice(Lattice.cubic(10), "F")
    assert abs(f.volume - 1000 / 4) < 1e-6
    r = GR.primitive_lattice(Lattice.hexagonal(10, 30), "R")
    assert abs(r.volume - Lattice.hexagonal(10, 30).volume / 3) < 1e-6


def test_lattice_match_tolerances():
    ref = GR.primitive_lattice(Lattice.from_parameters(10, 12, 14, 90, 100, 90), "P")
    ok = GR.primitive_lattice(Lattice.from_parameters(10.05, 12.06, 13.93, 90, 100.5, 90), "P")
    assert GR.lattice_match(ref, ok)
    bad_len = GR.primitive_lattice(Lattice.from_parameters(10.2, 12, 14, 90, 100, 90), "P")
    assert not GR.lattice_match(ref, bad_len)
    bad_ang = GR.primitive_lattice(Lattice.from_parameters(10, 12, 14, 90, 101.5, 90), "P")
    assert not GR.lattice_match(ref, bad_ang)
    sub = GR.primitive_lattice(Lattice.from_parameters(5, 12, 14, 90, 100, 90), "P")
    assert not GR.lattice_match(ref, sub)
    sup = GR.primitive_lattice(Lattice.from_parameters(20, 12, 14, 90, 100, 90), "P")
    assert not GR.lattice_match(ref, sup)


def test_lattice_match_setting_independence():
    # P21/c vs P21/n descriptions of the same lattice
    a, b, c, beta = 10.0, 12.0, 14.0, 110.0
    l1 = Lattice.from_parameters(a, b, c, 90, beta, 90)
    # alternative cell: a' = a + c
    m = l1.matrix
    l2 = Lattice([m[0] + m[2], m[1], m[2]])
    assert GR.lattice_match(GR.primitive_lattice(l1, "P"), GR.primitive_lattice(l2, "P"))
    # C-centred conventional vs its primitive description
    conv = Lattice.from_parameters(20, 8, 12, 90, 95, 90)
    prim = GR.primitive_lattice(conv, "C")
    assert GR.lattice_match(prim, GR.primitive_lattice(prim, "P"))


def test_count_data_blocks_and_smiles_graph():
    assert GR.count_data_blocks("data_a\n_x 1\ndata_b\n_y 2\n") == 2
    g = GR.smiles_graph("CC(=O)[O-]")
    assert g.number_of_nodes() == 4 and g.number_of_edges() == 3
    g2 = GR.smiles_graph("[Cl-]")
    assert g2.number_of_nodes() == 1


def _write_split_bet(tmp_path, json_sg, cif_sg, json_cell=(10, 12, 14, 90, 100, 90), cif_cell=(10, 12, 14, 90, 100, 90)):
    iid = "Xtest001"
    a, b, c, al, be, ga = cif_cell
    (tmp_path / f"{iid}.cif").write_text(
        f"data_x\n_cell_length_a {a}\n_cell_length_b {b}\n_cell_length_c {c}\n_cell_angle_alpha {al}\n_cell_angle_beta {be}\n"
        f"_cell_angle_gamma {ga}\n_symmetry_space_group_name_H-M '{cif_sg}'\nloop_\n_atom_site_label\n_atom_site_type_symbol\n"
        "_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\nC1 C 0.1 0.2 0.3\n")
    a, b, c, al, be, ga = json_cell
    (tmp_path / f"{iid}.json").write_text(
        '{"cell": {"a": %s, "b": %s, "c": %s, "alpha": %s, "beta": %s, "gamma": %s}, "space_group": "%s"}' % (a, b, c, al, be, ga, json_sg))
    return str(tmp_path / f"{iid}.json"), GR.read_cif_text(str(tmp_path / f"{iid}.cif"))


def test_cif_wins_when_files_agree(tmp_path):
    json_path, cif_text = _write_split_bet(tmp_path, "P 21/c", "P 21/c")
    lat, sg, cen, reason, consistent = GR.submitted_cell(json_path, cif_text)
    assert consistent and GR.sg_type(sg) == GR.sg_type(14) and abs(lat.b - 12) < 1e-6


def test_setting_change_still_agrees(tmp_path):
    # P 21/n JSON against a P 21/c CIF in the equivalent setting: same lattice type, same group type
    json_path, cif_text = _write_split_bet(tmp_path, "P 21/n", "P 21/c")
    assert GR.submitted_cell(json_path, cif_text)[4] is True


def test_split_bet_on_space_group_is_inconsistent(tmp_path):
    json_path, cif_text = _write_split_bet(tmp_path, "P 21/c", "P 21")
    lat, sg, cen, reason, consistent = GR.submitted_cell(json_path, cif_text)
    assert consistent is False and "different crystals" in reason


def test_split_bet_on_cell_is_inconsistent(tmp_path):
    json_path, cif_text = _write_split_bet(tmp_path, "P 21/c", "P 21/c", json_cell=(10, 12, 28, 90, 100, 90))
    assert GR.submitted_cell(json_path, cif_text)[4] is False


def test_json_alone_is_graded(tmp_path):
    json_path, _ = _write_split_bet(tmp_path, "P 21/c", "P 21/c")
    lat, sg, cen, reason, consistent = GR.submitted_cell(json_path, None)
    assert consistent and lat is not None and GR.sg_type(sg) == GR.sg_type(14)
