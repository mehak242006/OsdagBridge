"""Chapter 3 live-load tables (R3): vehicle live loads and footway live load.

Data extraction (``selected_vehicle_rows``, ``bridge_braking_force``,
``footway_rows``) is kept separate from presentation
(``vehicle_live_load_table``, ``footway_live_load_table``, built with PyLaTeX).

Every value comes from inputs or from functions the program already uses:

* vehicles       — only those ticked in Additional Inputs -> Loading
                   (``KEY_LL_IRC_*`` flags and ``KEY_LL_CUSTOM_VEHICLES``)
* total load     — ``BridgeGrillageModel._vehicle_total_weight_kN`` (IRC 6
                   vehicle definitions); vehicles without a definition show
                   ``NOT_COMPUTED``
* impact factor  — ``IRC6_2017.cl_208_2`` (Class A) / ``cl_208_3`` (Class 70R
                   and AA), same mapping the report used before
* braking        — "considered?" from the ``KEY_BL_IRC_*`` inputs (the GUI
                   offers it for Class SV only); per-vehicle braking forces are
                   not computed by OsdagBridge. The bridge braking force of
                   IRC 6 Cl. 211.2 is reported separately.
* centrifugal    — not computed by OsdagBridge (no horizontal-curvature input)
* footway load   — ``footpath_dead_load_kN_m2()``, the intensity the grillage
                   analysis applies (IRC 6 Cl. 206.1)
"""
from __future__ import annotations

from pylatex import LongTable, MultiColumn
from pylatex.utils import NoEscape

from osdagbridge.core.reports import styles as S
from osdagbridge.core.reports.report_utils import _tex, count_columns, fit_colspec
from osdagbridge.core.utils.common import (
    KEY_BL_ECCENTRICITY, KEY_BL_IRC_70R_BOGIE, KEY_BL_IRC_70R_TRACKED,
    KEY_BL_IRC_70R_WHEELED, KEY_BL_IRC_AA_TRACKED, KEY_BL_IRC_AA_WHEELED,
    KEY_BL_IRC_CLASS_A, KEY_BL_IRC_CLASS_FATIGUE, KEY_BL_IRC_CLASS_SV,
    KEY_CARRIAGEWAY_WIDTH, KEY_FOOTPATH, KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY, KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE, KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_CLASS_A, KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV, KEY_SPAN, KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_FOOTPATHS, KEY_WC_LD_LANE_TABLE_COUNT,
)

NOT_COMPUTED = "Not computed by OsdagBridge"

# (selection key, label, total-load vehicle type, impact-factor clause, braking key)
VEHICLE_CATALOGUE = [
    (KEY_LL_IRC_CLASS_A,       "Class A",             "ClassA",           "208.2", KEY_BL_IRC_CLASS_A),
    (KEY_LL_IRC_70R_WHEELED,   "Class 70R (Wheeled)", "Class70R",         "208.3", KEY_BL_IRC_70R_WHEELED),
    (KEY_LL_IRC_70R_TRACKED,   "Class 70R (Tracked)", "Class70R_Tracked", "208.3", KEY_BL_IRC_70R_TRACKED),
    (KEY_LL_IRC_AA_WHEELED,    "Class AA (Wheeled)",  None,               "208.3", KEY_BL_IRC_AA_WHEELED),
    (KEY_LL_IRC_AA_TRACKED,    "Class AA (Tracked)",  None,               "208.3", KEY_BL_IRC_AA_TRACKED),
    (KEY_LL_IRC_CLASS_SV,      "Class SV",            "ClassSV",          None,    KEY_BL_IRC_CLASS_SV),
    (KEY_LL_IRC_70R_BOGIE,     "Class 70R (Bogie)",   None,               "208.3", KEY_BL_IRC_70R_BOGIE),
    (KEY_LL_IRC_CLASS_FATIGUE, "Class Fatigue",       "Fatigue",          None,    KEY_BL_IRC_CLASS_FATIGUE),
]


def _is_selected(value) -> bool:
    """GUI check boxes are saved as True/False or 1/0 (and occasionally strings)."""
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _impact_factor(clause, span_m):
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    if clause is None or span_m is None:
        return None
    try:
        im = (IRC6_2017.cl_208_2_impact_factor(span_m) if clause == "208.2"
              else IRC6_2017.cl_208_3_impact_factor(span_m))
        return 1.0 + float(im)
    except Exception:
        return None


def _total_load_kN(vehicle_type):
    if vehicle_type is None:
        return None
    from osdagbridge.core.bridge_types.plate_girder.analyser import BridgeGrillageModel
    value = BridgeGrillageModel._vehicle_total_weight_kN(vehicle_type)
    return value if value and value > 0 else None


# ═══════════════════════════════════════════════════════════════════════════
# Data extraction
# ═══════════════════════════════════════════════════════════════════════════

def selected_vehicle_rows(input_dict: dict) -> list[dict]:
    """One row per vehicle selected in the Loading tab (IRC vehicles, then custom).

    Keys: ``label``, ``total_kN``, ``impact_factor``, ``impact_clause``,
    ``braking_considered`` (True / False / None = option not offered),
    ``eccentricity_m``. ``None`` means "not computed".
    """
    span_m = _float(input_dict.get(KEY_SPAN))
    ecc = _float(input_dict.get(KEY_LL_ECCENTRICITY, input_dict.get(KEY_BL_ECCENTRICITY)))
    rows = []
    for sel_key, label, vtype, clause, bl_key in VEHICLE_CATALOGUE:
        if not _is_selected(input_dict.get(sel_key)):
            continue
        considered = _is_selected(input_dict[bl_key]) if bl_key in input_dict else None
        rows.append({
            "label": label,
            "total_kN": _total_load_kN(vtype),
            "impact_factor": _impact_factor(clause, span_m),
            "impact_clause": clause,
            "braking_considered": considered,
            "eccentricity_m": ecc if considered else None,
        })
    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES) or []
    if isinstance(custom, list):
        for c in custom:
            name = c.get("name") if isinstance(c, dict) else c if isinstance(c, str) else None
            if name:
                rows.append({"label": str(name), "total_kN": None, "impact_factor": None,
                             "impact_clause": None, "braking_considered": None,
                             "eccentricity_m": None})
    return rows


def design_lanes(input_dict: dict):
    """(number of design lanes, source text) or (None, reason).

    Uses the stored lane count when present, otherwise IRC 6 Table 6 for the
    carriageway width - the rule the grillage analysis uses to place lanes.
    """
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    stored = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    if stored not in (None, ""):
        try:
            return int(stored), "Lane Details input"
        except (TypeError, ValueError):
            pass
    width = _float(input_dict.get(KEY_CARRIAGEWAY_WIDTH))
    if width is None:
        return None, "carriageway width not available"
    try:
        return int(IRC6_2017.table_6(width)), f"IRC 6 Table 6, carriageway width {width:g} m"
    except Exception:
        return None, "IRC 6 Table 6 not applicable"


def bridge_braking_force(input_dict: dict):
    """IRC 6 Cl. 211.2 braking force for the design lanes, or None."""
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    lanes, source = design_lanes(input_dict)
    if lanes is None:
        return None
    try:
        tonnes = float(IRC6_2017.cl_211_2_braking_force(lanes))
    except Exception:
        return None
    return {"lanes": lanes, "lane_source": source, "tonnes": tonnes, "kN": tonnes * 9.81}


def footway_rows(input_dict: dict) -> list[tuple[str, str, str]]:
    """(parameter, value, unit) rows of the footway live-load table."""
    footpath = str(input_dict.get(KEY_FOOTPATH, "None") or "None").strip()
    has_footpath = footpath.lower() not in ("none", "")
    mode = str(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "") or "").strip()
    user_value = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    rows = [("Footpath", footpath, "---")]
    if not has_footpath:
        rows.append(("Footway live load", "Not applicable (no footpath)", "---"))
        return rows
    rows += [
        ("Number of footpaths", str(input_dict.get(KEY_TS_NO_OF_FOOTPATHS, "") or "---"), "---"),
        ("Footpath width", str(input_dict.get(KEY_TS_FOOTPATH_WIDTH, "") or "---"), "m"),
        ("Footway pressure option (input)", mode or "---", "---"),
    ]
    if user_value not in (None, ""):
        rows.append(("User-defined footway pressure (input)", str(user_value), "kN/m²"))
    try:
        from osdagbridge.core.bridge_components.super_structure.footpath.geometry import (
            footpath_dead_load_kN_m2,
        )
        applied = f"{float(footpath_dead_load_kN_m2()):.3f}"
    except Exception:
        applied = NOT_COMPUTED
    rows.append(("Footway live load applied in analysis (IRC 6 Cl. 206.1)", applied, "kN/m²"))
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Presentation (PyLaTeX)
# ═══════════════════════════════════════════════════════════════════════════

# "Not computed" marker: full wording, set small so it fits narrow columns
NC_CELL = r"{\osdagFootnoteFont\itshape " + NOT_COMPUTED + "}"
# compact padding for the 7-column vehicle table (scoped to that table)
VEHICLE_TABLE_COLSEP = S.LENGTHS["osdagColSepCompact"]


def _nc(value, fmt):
    return NoEscape(_tex(fmt.format(value))) if value is not None else NoEscape(NC_CELL)


def _repeating_longtable(colspec, header_rows, caption, ncols, tabcolsep=None):
    """PyLaTeX LongTable whose header rows repeat on every page."""
    # PyLaTeX cannot count columns of the custom L{}/C{} types; give it the width.
    table = LongTable(NoEscape(fit_colspec(colspec, tabcolsep=tabcolsep)),
                      width=count_columns(colspec))
    for first in (True, False):
        cap = caption if first else caption + " " + S.TABLE_CONTINUED_SUFFIX
        table.append(NoEscape(r"\caption" + ("" if first else "[]") + "{" + cap + r"}\\"))
        table.add_hline()
        for row in header_rows:
            table.append(NoEscape(r"\rowcolor{osdagTableHeader}" + row))
        table.add_hline()
        table.append(NoEscape(r"\endfirsthead" if first else r"\endhead"))
    table.add_row((MultiColumn(ncols, align="r",
                               data=NoEscape(r"\osdagFootnoteFont " + S.TABLE_CONTINUES_NOTE)),))
    table.append(NoEscape(r"\endfoot"))
    table.append(NoEscape(r"\endlastfoot"))
    return table


def vehicle_live_load_table(rows: list[dict], braking: dict | None, span_m: float | None) -> str:
    """Vehicle live-load table + notes (LaTeX string)."""
    header = [
        r"\textbf{Vehicle} & \textbf{Total Load} & \textbf{Impact Factor}"
        r" & \multicolumn{3}{c|}{\textbf{Braking Load}} & \textbf{Centrifugal} \\"
        "\n" r"\cline{4-6}",
        r" & \textbf{(kN)} & \textbf{(1 + IM)} & \textbf{Considered?} & \textbf{Value (kN)}"
        r" & \textbf{Eccentricity (m)} & \textbf{Force (kN)} \\[\osdagRowPad]",
    ]
    colspec = r"|L{2.9cm}|C{1.9cm}|C{1.9cm}|C{2.1cm}|C{2.5cm}|C{2.3cm}|C{2.5cm}|"
    table = _repeating_longtable(colspec, header, r"\textbf{Vehicle Live Loads (LL) --- Selected Vehicles}", 7,
                                 tabcolsep=VEHICLE_TABLE_COLSEP)
    if not rows:
        table.add_row((MultiColumn(7, align="|c|", data="No vehicle selected in Additional Inputs"),))
        table.add_hline()
    for r in rows:
        considered = {True: "Yes", False: "No", None: "---"}[r["braking_considered"]]
        table.add_row((
            NoEscape(_tex(r["label"])),
            _nc(r["total_kN"], "{:.2f}"),
            _nc(r["impact_factor"], "{:.3f}"),
            considered,
            NoEscape(NC_CELL) if r["braking_considered"] else "---",
            _nc(r["eccentricity_m"], "{:.2f}") if r["braking_considered"] else "---",
            NoEscape(NC_CELL),
        ))
        table.add_hline()

    if braking:
        brake = (f"{braking['kN']:.2f} kN ({braking['tonnes']:.2f} t) for {braking['lanes']} design "
                 f"lane(s) ({braking['lane_source']}). It is not applied in the grillage analysis.")
    else:
        brake = NOT_COMPUTED + "."
    notes = [
        r"Total load: unfactored gross vehicle load from the IRC~6 vehicle definitions in OsdagBridge.",
        r"Impact factor: IRC~6 Cl.~208.2 (Class~A) and Cl.~208.3 (Class~70R / AA) for span $L$ = "
        + (_tex(f"{span_m:g}") + r"~m" if span_m is not None else "---")
        + r"; not computed by OsdagBridge for Class~SV and the fatigue vehicle.",
        r"Braking ``Considered?'' is the Additional Inputs $\rightarrow$ Loading selection, offered for "
        r"Class~SV only (--- = not offered). Per-vehicle braking forces are not computed by "
        r"OsdagBridge. Bridge braking force, IRC~6 Cl.~211.2: " + _tex(brake),
        r"Centrifugal forces: not computed by OsdagBridge --- there is no horizontal-curvature "
        r"input; the bridge is modelled as straight in plan.",
    ]
    note_tex = (r"\noindent{\osdagFootnoteFont\textit{Notes:}" "\n"
                r"\begin{enumerate}[nosep,leftmargin=*]" "\n"
                + "\n".join(r"\item " + n for n in notes)
                + "\n" r"\end{enumerate}}" "\n")
    return ("\\begingroup\n\\setlength{\\tabcolsep}{\\osdagColSepCompact}\n"
            + table.dumps() + "\n\\endgroup\n" + note_tex)


def footway_live_load_table(rows: list[tuple[str, str, str]]) -> str:
    table = _repeating_longtable(r"|L{8.0cm}|C{5.0cm}|C{2.4cm}|",
                                 [r"\textbf{Parameter} & \textbf{Value} & \textbf{Unit} \\[\osdagRowPad]"],
                                 r"\textbf{Footway Live Load}", 3)
    for param, value, unit in rows:
        table.add_row((NoEscape(_tex(param)), NoEscape(_tex(value)),
                       NoEscape(r"kN/m\textsuperscript{2}" if unit == "kN/m²" else _tex(unit))))
        table.add_hline()
    return table.dumps() + "\n"
