"""R4 (utilization ratio charts) and R5 (material quantity charts)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from osdagbridge.core.reports import charts as Ch
from osdagbridge.core.reports import styles as S
from osdagbridge.core.reports import ur_summary as U
from osdagbridge.core.reports.chap7 import ch7_quantities, quantity_chart_data
from osdagbridge.core.reports.report_generator import ReportDataBridge

C = S.CHART


def _bars(ax):
    return [p for p in ax.patches if p.get_width() > 0 or p.get_height() > 0]


def _threshold_lines(ax):
    return [ln for ln in ax.lines if list(ln.get_ydata()) == [1.0, 1.0]]


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


# ── R4 ────────────────────────────────────────────────────────────────────

def test_panel_has_red_dashed_threshold_at_one_and_ur_label():
    fig, ax = plt.subplots()
    Ch.ur_bar_panel(ax, "Elem", [("A", 0.5), ("B", 1.2)])
    lines = _threshold_lines(ax)
    assert len(lines) == 1
    assert lines[0].get_color() == "red" and lines[0].get_linestyle() == "--"
    assert ax.get_ylabel() == "Utilization Ratio"


def test_pass_and_fail_bars_are_distinguished():
    fig, ax = plt.subplots()
    Ch.ur_bar_panel(ax, "Elem", [("ok", 0.99), ("exactly", 1.0), ("bad", 1.01)])
    colors = [p.get_facecolor() for p in _bars(ax)]
    good, edge, bad = colors
    assert good == edge                      # UR = 1.0 passes (UR <= 1.0)
    assert good != bad
    assert _bars(ax)[2].get_hatch() == C["fail_hatch"]      # fail also hatched, not colour-only
    assert _bars(ax)[0].get_hatch() is None


def test_missing_ur_is_not_plotted_as_zero():
    fig, ax = plt.subplots()
    Ch.ur_bar_panel(ax, "Elem", [("x", None), ("y", 0.4)])
    texts = [t.get_text() for t in ax.texts]
    assert "n/a" in texts and "0.40" in texts
    assert "0.00" not in texts


def test_empty_panel_shows_note_and_threshold():
    fig, ax = plt.subplots()
    Ch.ur_bar_panel(ax, "End Diaphragms", [], note="No member design")
    assert any("No member design" in t.get_text() for t in ax.texts)
    assert len(_threshold_lines(ax)) == 1
    assert not _bars(ax)


def test_figure_has_the_four_elements():
    summary = {k: {"checks": [("c", 0.5)], "note": None}
               for k in ("Steel Plate Girders", "Concrete Deck Slab", "Cross Bracing", "End Diaphragms")}
    fig = Ch.build_ur_figure(summary)
    assert [a.get_title(loc="left") for a in fig.axes[:4]] == list(summary)
    assert all(len(_threshold_lines(a)) == 1 for a in fig.axes[:4])


def _bridge(**output):
    return ReportDataBridge(output, {}, None)


def test_summary_takes_urs_from_design_results_and_marks_unavailable():
    pg = {"G1": {"checks": [{"check_id": 1, "dcr": 0.4, "demand": 1, "capacity": 2},
                            {"check_id": 2, "dcr": 1.3, "demand": 3, "capacity": 2}]},
          "G2": {"checks": [{"check_id": 1, "dcr": 0.6, "demand": 1, "capacity": 2}]}}
    summary = U.overall_ur_summary(_bridge(design_results={"per_girder": pg}))
    girders = dict(summary["Steel Plate Girders"]["checks"])
    assert girders["Moment"] == 0.6            # worst girder governs
    assert girders["Shear"] == 1.3
    assert girders["Fatigue"] is None          # no result -> None, not 0
    assert summary["Concrete Deck Slab"]["note"]
    assert summary["End Diaphragms"]["checks"] == []
    assert set(summary) == {"Steel Plate Girders", "Concrete Deck Slab", "Cross Bracing", "End Diaphragms"}


def test_empty_results_do_not_raise():
    fig = Ch.build_ur_figure(U.overall_ur_summary(_bridge()))
    assert len(fig.axes) >= 4


def test_deck_ur_is_demand_over_capacity():
    r = U.deck_ratio({"x": 0, "dem": 50.0, "cap": 100.0}, "dem", "cap")
    assert r["ur"] == pytest.approx(0.5)
    assert U.deck_ratio({}, "dem", "cap") is None


# ── temporary image handling / PyLaTeX embedding ──────────────────────────

def test_save_chart_writes_png_to_given_directory(tmp_path):
    fig = Ch.build_quantity_figure([("Girders", 1.0)], 2.0, 3.0)
    path = Ch.save_chart(fig, str(tmp_path / "charts"), "q")
    assert os.path.isfile(path) and path.endswith("q.png")
    assert os.path.getsize(path) > 1000
    assert not plt.get_fignums()               # figure closed after saving


def test_chart_figure_tex_is_a_pylatex_figure():
    tex = Ch.chart_figure_tex("charts\\ur.png", "Cap", label="fig:x")
    assert r"\begin{figure}[H]" in tex and "charts/ur.png" in tex
    assert r"\caption{Cap}" in tex and r"\label{fig:x}" in tex


def test_chapter7_without_chart_dir_adds_no_figure():
    assert "includegraphics" not in ch7_quantities({}, None)


def test_chapter7_embeds_chart_and_leaves_no_files_outside_dir(tmp_path):
    inp = {"steel_girders_wt_total": "51.75", "bracing_top_wt_total": "0.02",
           "bracing_bot_wt_total": "0.02", "bracing_diag_wt_total": "0.04",
           "concrete_deck_vol_total": "104.56", "rebar_deck_wt_total": "12.55"}
    d = tmp_path / "charts"
    tex = ch7_quantities(inp, str(d))
    assert "charts/quantities.png" in tex and (d / "quantities.png").is_file()
    assert [p.name for p in tmp_path.iterdir()] == ["charts"]


# ── R5 ────────────────────────────────────────────────────────────────────

def test_quantity_data_matches_table_values():
    inp = {"steel_girders_wt_total": "51.75", "bracing_top_wt_total": "0.02",
           "bracing_bot_wt_total": "0.02", "bracing_diag_wt_total": "0.04",
           "concrete_deck_vol_total": "104.56", "rebar_deck_wt_total": "12.55"}
    steel, concrete, rebar = quantity_chart_data(inp)
    assert steel[0] == ("Girders", 51.75)
    assert steel[1] == ("Cross bracing", pytest.approx(0.08))
    assert steel[2] == ("End diaphragms", None)       # no BOQ value: never invented
    assert (concrete, rebar) == (104.56, 12.55)
    tex = ch7_quantities(inp, None)                   # the same numbers are in Table 7.1
    assert "51.75" in tex and "104.56" in tex and "12.55" in tex


def test_missing_quantities_are_none_not_zero():
    steel, concrete, rebar = quantity_chart_data({"steel_girders_wt_total": "N.A.",
                                                  "bracing_top_wt_total": "0.02"})
    assert steel[0][1] is None and steel[1][1] is None
    assert concrete is None and rebar is None


def test_quantity_figure_uses_separate_axes_with_distinct_units():
    fig = Ch.build_quantity_figure([("Girders", 51.75), ("Cross bracing", 0.08), ("End diaphragms", None)],
                                   104.56, 12.55)
    steel, conc, reb = fig.axes
    assert steel.get_ylabel() == "Weight (MT)"
    assert conc.get_ylabel() == "Volume (m³)"
    assert reb.get_ylabel() == "Weight (MT)"
    assert [round(p.get_height(), 2) for p in _bars(conc)] == [104.56]
    assert [round(p.get_height(), 2) for p in _bars(reb)] == [12.55]
    assert "n/a" in [t.get_text() for t in steel.texts]


def test_all_missing_quantities_produce_no_figure(tmp_path):
    assert "includegraphics" not in ch7_quantities({}, str(tmp_path))
    assert not list(tmp_path.iterdir())
