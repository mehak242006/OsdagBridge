"""Section 5.4 End Diaphragm tables use end-diaphragm results, not cross bracing."""
from osdagbridge.core.reports.chap5 import _ed_not_designed_message, _transverse_member_rows
from osdagbridge.core.reports.report_generator import EndDiaphragmDataBridge, ReportDataBridge
from osdagbridge.core.utils.common import KEY_MP_ED_BRACING_SECTION_DESIGNATION, KEY_MP_ED_TYPE

NONE_FORCES = {k: None for k in ("diag_tension_kN", "diag_tension_gov_lc", "diag_compression_kN",
                                 "diag_compression_gov_lc", "chord_tension_kN", "chord_tension_gov_lc")}


def _output(ed_forces=None, ed_designs=None):
    return {
        # cross bracing: real forces / designs / small angle section properties
        "crossbracing_forces_dict": {"pairs": {"G1-G2": {"diag_tension_kN": 10.2, "diag_compression_kN": 12.9,
                                                         "chord_tension_kN": 8.9}}},
        "crossbracing_design_results": {"G1-G2": {"diagonal": {"tension": {}}}},
        "transverse_member_design.cb.section_properties.bracing.G1G2.A": 2.37,
        "transverse_member_design.cb.section_properties.bracing.G1G2.rv": 0.80,
        # end diaphragm: as produced by the reference design
        "end_diaphragm_forces_dict": {"pairs": {"G1-G2": dict(ed_forces or NONE_FORCES)}},
        "end_diaphragm_design_results": ed_designs if ed_designs is not None else {"G1-G2": {}},
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A": 19.10,
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.rv": 1.97,
    }


INPUTS = {f"{KEY_MP_ED_TYPE}.G1G2.E1M1": "Cross Bracing",
          f"{KEY_MP_ED_BRACING_SECTION_DESIGNATION}.G1G2.E1M1": "IS 100 x 100 x 10"}


def test_end_diaphragm_view_reads_end_diaphragm_data():
    bridge = ReportDataBridge(_output(), INPUTS, None)
    ed = bridge.end_diaphragm()
    assert isinstance(ed, EndDiaphragmDataBridge)
    assert bridge.get_cb_force("G1-G2", "diagonal", "tension") == "10.200"
    assert ed.get_cb_force("G1-G2", "diagonal", "tension") == ""        # ED force is None
    assert bridge.has_member_designs() and not ed.has_member_designs()


def test_end_diaphragm_section_table_uses_ed_properties_and_section():
    ed = ReportDataBridge(_output(), INPUTS, None).end_diaphragm()
    forces, _, _ = _transverse_member_rows(ed)
    assert "1910.0" in forces and "19.7" in forces          # ED A = 19.10 cm2, rv = 1.97 cm
    assert "237.0" not in forces                            # not the cross-bracing area
    assert "IS 100 x 100 x 10" in forces                    # ED section from the inputs
    # pair label once per pair
    assert forces.count(r"\makecell{G1-G2}") == 1


def test_cross_bracing_tables_unchanged_source():
    forces, _, _ = _transverse_member_rows(ReportDataBridge(_output(), INPUTS, None))
    assert "237.0" in forces and "1910.0" not in forces


def test_not_designed_message_states_the_threshold_reason():
    ed = ReportDataBridge(_output(), INPUTS, None).end_diaphragm()
    msg = _ed_not_designed_message(ed)
    assert "0.005" in msg and "no member was designed" in msg


def test_not_designed_message_for_rolled_or_welded_end_diaphragms():
    inputs = {f"{KEY_MP_ED_TYPE}.G1G2.E1M1": "Rolled Beam"}
    ed = ReportDataBridge(_output(), inputs, None).end_diaphragm()
    assert "not implemented" in _ed_not_designed_message(ed)


def test_designs_present_are_detected():
    ed = ReportDataBridge(_output(ed_designs={"G1-G2": {"diagonal": {"compression": {"x": 1}}}}),
                          INPUTS, None).end_diaphragm()
    assert ed.has_member_designs()
