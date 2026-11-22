"""R3 — Chapter 3 vehicle live-load and footway live-load tables."""
import pytest

from osdagbridge.core.reports.chap3 import ch3_loads
from osdagbridge.core.reports.live_load_tables import (
    NC_CELL, NOT_COMPUTED, bridge_braking_force, design_lanes, footway_live_load_table,
    footway_rows, selected_vehicle_rows, vehicle_live_load_table,
)
from osdagbridge.core.utils.codes.keyfile import g
from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV, KEY_CARRIAGEWAY_WIDTH, KEY_FOOTPATH, KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY, KEY_LL_FOOTPATH_PRESSURE_MODE, KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_CLASS_A, KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV, KEY_SPAN, KEY_TS_FOOTPATH_WIDTH, KEY_TS_NO_OF_FOOTPATHS,
)

ALL_VEHICLE_KEYS = [KEY_LL_IRC_CLASS_A, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_70R_TRACKED,
                    KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_AA_TRACKED, KEY_LL_IRC_CLASS_SV,
                    KEY_LL_IRC_70R_BOGIE, KEY_LL_IRC_CLASS_FATIGUE]


def _inputs(selected, **extra):
    d = {k: (1 if k in selected else 0) for k in ALL_VEHICLE_KEYS}
    d.update({KEY_SPAN: "35", KEY_CARRIAGEWAY_WIDTH: "7.5", KEY_LL_ECCENTRICITY: "1.2",
              KEY_BL_IRC_CLASS_SV: True, KEY_FOOTPATH: "Both Sides",
              KEY_TS_NO_OF_FOOTPATHS: 2, KEY_TS_FOOTPATH_WIDTH: 1.5,
              KEY_LL_FOOTPATH_PRESSURE_MODE: "As per IRC 6", KEY_LL_CUSTOM_VEHICLES: []})
    d.update(extra)
    return d


REFERENCE = [KEY_LL_IRC_CLASS_A, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_70R_TRACKED,
             KEY_LL_IRC_CLASS_SV, KEY_LL_IRC_CLASS_FATIGUE]


def test_reference_selection_lists_exactly_the_selected_vehicles():
    labels = [r["label"] for r in selected_vehicle_rows(_inputs(REFERENCE))]
    assert labels == ["Class A", "Class 70R (Wheeled)", "Class 70R (Tracked)",
                      "Class SV", "Class Fatigue"]


def test_a_different_selection_changes_the_table():
    d = _inputs([KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_AA_TRACKED, KEY_LL_IRC_70R_BOGIE],
                **{KEY_LL_CUSTOM_VEHICLES: [{"name": "Crane 120t"}]})
    rows = selected_vehicle_rows(d)
    assert [r["label"] for r in rows] == ["Class AA (Wheeled)", "Class AA (Tracked)",
                                         "Class 70R (Bogie)", "Crane 120t"]
    # no IRC6 definitions exist for these -> not computed, never zero
    assert all(r["total_kN"] is None for r in rows)
    tex = vehicle_live_load_table(rows, None, 35.0)
    assert "Class A " not in tex and "Class SV" not in tex
    assert tex.count(NOT_COMPUTED) >= 4


def test_unticked_vehicles_stored_as_zero_or_false_are_excluded():
    d = _inputs([KEY_LL_IRC_CLASS_A], **{KEY_LL_IRC_70R_WHEELED: False, KEY_LL_IRC_CLASS_SV: "0"})
    assert [r["label"] for r in selected_vehicle_rows(d)] == ["Class A"]


def test_values_come_from_program_functions():
    rows = {r["label"]: r for r in selected_vehicle_rows(_inputs(REFERENCE))}
    assert rows["Class A"]["total_kN"] == pytest.approx(55.4 * g)
    assert rows["Class SV"]["total_kN"] == pytest.approx(385.0 * g)
    assert rows["Class A"]["impact_factor"] == pytest.approx(1.186, abs=1e-3)      # Cl. 208.2, L=35
    assert rows["Class 70R (Wheeled)"]["impact_factor"] == pytest.approx(1.100, abs=1e-3)  # Cl. 208.3
    assert rows["Class SV"]["impact_factor"] is None
    assert rows["Class Fatigue"]["impact_factor"] is None
    # braking selection exists for SV only
    assert rows["Class SV"]["braking_considered"] is True
    assert rows["Class SV"]["eccentricity_m"] == pytest.approx(1.2)
    assert rows["Class A"]["braking_considered"] is None


def test_braking_and_centrifugal_marked_not_computed_per_vehicle():
    tex = vehicle_live_load_table(selected_vehicle_rows(_inputs(REFERENCE)),
                                  bridge_braking_force(_inputs(REFERENCE)), 35.0)
    # 5 centrifugal cells (one per vehicle) + SV braking value + impact factor
    # of SV and Fatigue; every total load of the reference selection is computed
    assert tex.count(NC_CELL) == 5 + 1 + 2
    assert "centrifugal" in tex.lower() and "not computed" in tex.lower()


def test_bridge_braking_force_uses_fixed_irc_function():
    b = bridge_braking_force(_inputs(REFERENCE))
    assert b["lanes"] == 2 and "Table 6" in b["lane_source"]
    assert b["tonnes"] == pytest.approx(11.08, abs=1e-3)
    assert b["kN"] == pytest.approx(11.08 * 9.81, abs=1e-2)


def test_design_lanes_unavailable_without_width():
    assert design_lanes({})[0] is None
    assert bridge_braking_force({}) is None


def test_table_header_repeats_and_follows_pdf_structure():
    tex = vehicle_live_load_table(selected_vehicle_rows(_inputs(REFERENCE)), None, 35.0)
    for needed in (r"\endfirsthead", r"\endhead", r"\multicolumn{3}{c|}{\textbf{Braking Load}}",
                   "Considered?", "Value (kN)", "Eccentricity (m)", "Total Load", "Impact Factor"):
        assert needed in tex, needed


def test_footway_table_is_separate_and_uses_applied_intensity():
    rows = footway_rows(_inputs(REFERENCE))
    applied = [v for p, v, u in rows if "applied in analysis" in p]
    assert applied == ["4.905"]                       # IRC 6 Cl. 206.1, 500 kg/m2
    assert footway_rows(_inputs(REFERENCE, **{KEY_FOOTPATH: "None"}))[-1][1].startswith("Not applicable")
    assert r"\textbf{Footway Live Load}" in footway_live_load_table(rows)


def test_chapter3_has_separate_vehicle_and_footway_tables():
    tex = ch3_loads(_inputs(REFERENCE))
    assert "Vehicle Live Loads (LL)" in tex and "Footway Live Load" in tex
    assert tex.index("Vehicle Live Loads (LL)") < tex.index("Footway Live Load")
    assert "Vehicles Considered" not in tex           # old merged table removed
