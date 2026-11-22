"""Governing utilization ratios (UR = demand / capacity) for Section 5.5.

Single data source for both the Overall Design Check Summary table and the
UR charts (R4). Every function only *selects* values the design stage already
computed - nothing is recalculated:

* plate girders  - ``design_results["per_girder"][G]["checks"]`` (DCR engine),
                   worst girder by DCR; per-load-case results as fallback for
                   SLS-conditional checks (deflection)
* deck slab      - ``deck_report_values`` (``KEY_DD_*``): UR = demand / capacity
                   of the stored values; crack width = governing w_k / limit
* cross bracing  - ``crossbracing_design_results`` member efficiencies (Osdag)
* end diaphragms - ``end_diaphragm_design_results`` (same accessors)
"""
from __future__ import annotations

from osdagbridge.core.utils.common import (
    KEY_DD_HAS_OVERHANG, KEY_DD_MU_BOT, KEY_DD_MU_OH, KEY_DD_MU_TOP,
    KEY_DD_M_ULS_HOG, KEY_DD_M_ULS_OH, KEY_DD_M_ULS_SAG, KEY_DD_PUNCH_VED,
    KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC, KEY_DD_VRD_C_MPA, KEY_DD_WK_BOT,
    KEY_DD_WK_LIMIT, KEY_DD_WK_OH, KEY_DD_WK_TOP,
)

# (label in Table 5.29, label in the chart, check ids, fallback unit)
GIRDER_CHECKS = [
    ("Girder --- Moment",         "Moment",      {1},      ""),
    ("Girder --- Shear",          "Shear",       {2},      ""),
    ("Girder --- LTB (constr.)",  "LTB (constr.)", {5},    ""),
    ("Girder --- Deflection",     "Deflection",  {13, 14}, "mm"),
    ("Girder --- Stress",         "Stress",      {11},     "MPa"),
    ("Girder --- Fatigue",        "Fatigue",     {8, 9},   "MPa"),
]
SLAB_TRANSVERSE_SHEAR_IDS = {16}

# (label in Table 5.29, chart label, demand key, capacity key, unit, is overhang)
DECK_CHECKS = [
    ("Deck --- Flexure (sagging)",   "Flexure (sag.)",  KEY_DD_M_ULS_SAG, KEY_DD_MU_BOT,     "kN-m/m", False),
    ("Deck --- Flexure (hogging)",   "Flexure (hog.)",  KEY_DD_M_ULS_HOG, KEY_DD_MU_TOP,     "kN-m/m", False),
    ("Deck --- Cantilever Overhang", "Overhang",        KEY_DD_M_ULS_OH,  KEY_DD_MU_OH,      "kN-m/m", True),
    ("Deck --- Punching Shear",      "Punching shear",  KEY_DD_PUNCH_VED, KEY_DD_VRD_C_MPA,  "MPa",    False),
    ("Deck --- One-Way Shear",       "One-way shear",   KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC, "kN/m",   False),
]

CB_SLENDERNESS_LIMITS = {"diagonal": 250.0, "chord": 400.0}


def _float(v, default=None):
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── plate girders ─────────────────────────────────────────────────────────

def per_girder(output_dict):
    return (output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}


def girder_governing(pg: dict, check_ids, fallback_unit: str = ""):
    """Worst girder (by DCR) for ``check_ids``.

    Returns a dict with ``ur, demand, capacity, demand_unit, capacity_unit``
    and either ``girder`` (from ``checks``) or ``lc`` (per-LC fallback), or None.
    """
    best = None
    for g, gd in pg.items():
        if str(g).startswith("EB"):
            continue
        for chk in (gd.get("checks") or []):
            if chk.get("check_id") in check_ids:
                d = chk.get("dcr") or 0.0
                if best is None or d > best["ur"]:
                    best = {"ur": d, "demand": chk.get("demand"), "capacity": chk.get("capacity"),
                            "demand_unit": chk.get("demand_unit") or "",
                            "capacity_unit": chk.get("capacity_unit") or "", "girder": g}
    if best is not None:
        return best
    for g, gd in pg.items():
        if str(g).startswith("EB"):
            continue
        for lc, ld in (gd.get("per_lc") or {}).items():
            if str(lc).lower().startswith("envelope"):
                continue
            for chk in (ld.get("checks") or []):
                if chk.get("id") in check_ids:
                    d = chk.get("dcr") or 0.0
                    if best is None or d > best["ur"]:
                        best = {"ur": d, "demand": chk.get("demand"), "capacity": chk.get("capacity"),
                                "demand_unit": fallback_unit, "capacity_unit": fallback_unit, "lc": lc}
    return best


def girder_governing_lc(pg: dict, girder, check_ids):
    """Load combination with the highest DCR for ``check_ids`` on ``girder``."""
    best = None
    for lc, ld in ((pg.get(girder) or {}).get("per_lc") or {}).items():
        if str(lc).lower().startswith("envelope"):
            continue
        for chk in (ld.get("checks") or []):
            if chk.get("id") in check_ids:
                d = chk.get("dcr") or 0.0
                if best is None or d > best[0]:
                    best = (d, lc)
    return best[1] if best else None


# ── deck slab ─────────────────────────────────────────────────────────────

def deck_values(output_dict):
    return output_dict.get("deck_report_values", {}) or {}


def deck_ratio(deck_rpt: dict, dem_key, cap_key, is_overhang=False):
    """{'demand', 'capacity', 'ur'} for one deck check; ``None`` if the deck
    design was not run, ``'n/a'`` for an overhang check without overhang."""
    if not deck_rpt:
        return None
    if is_overhang and not deck_rpt.get(KEY_DD_HAS_OVERHANG):
        return "n/a"
    dem = _float(deck_rpt.get(dem_key), 0.0)
    cap = _float(deck_rpt.get(cap_key), 0.0)
    return {"demand": dem, "capacity": cap, "ur": (dem / cap) if cap > 0 else None}


def deck_crack_ratio(deck_rpt: dict):
    """Governing crack width (max of bottom / top / overhang) against the limit."""
    if not deck_rpt:
        return None
    wks = [_float(deck_rpt.get(KEY_DD_WK_BOT), 0.0), _float(deck_rpt.get(KEY_DD_WK_TOP), 0.0)]
    if deck_rpt.get(KEY_DD_HAS_OVERHANG):
        wks.append(_float(deck_rpt.get(KEY_DD_WK_OH), 0.0))
    wk = max(wks)
    lim = _float(deck_rpt.get(KEY_DD_WK_LIMIT), 0.0)
    return {"demand": wk, "capacity": lim, "ur": (wk / lim) if lim > 0 else None}


# ── cross bracing / end diaphragms ────────────────────────────────────────

def member_governing(data, force_type):
    """Worst pair/member by Osdag efficiency for ``force_type``
    (``data`` = ReportDataBridge or its end_diaphragm() view)."""
    best = None
    for pair in data.get_cb_pairs():
        for member in ("diagonal", "chord"):
            cap = data.get_cb_capacity(pair, member, force_type)
            ur = _float(data.get_cb_efficiency(pair, member, force_type))
            if ur is None:
                continue
            if best is None or ur > best["ur"]:
                best = {"ur": ur, "pair": pair, "member": member, "capacity": cap}
    return best


def slenderness_governing(data):
    """Worst KL/r relative to its limit (250 diagonal / compression, 400 chord)."""
    best = None
    for pair in data.get_cb_pairs():
        for member in ("diagonal", "chord"):
            slend = _float(data.get_cb_slenderness(pair, member))
            if slend is None:
                continue
            lim = CB_SLENDERNESS_LIMITS[member]
            ratio = slend / lim
            if best is None or ratio > best["ur"]:
                best = {"ur": ratio, "slenderness": slend, "limit": lim}
    return best


# ── all elements, for the charts ──────────────────────────────────────────

def _ur(entry):
    if isinstance(entry, dict):
        return entry.get("ur")
    return None


def overall_ur_summary(bridge) -> dict:
    """Governing UR per check, grouped by element, for the R4 charts.

    ``{element: {"checks": [(label, ur or None)], "note": str or None}}``.
    ``None`` marks a check without a computed UR; it is drawn as
    "not available", never as zero.
    """
    od = bridge.output_dict
    pg = per_girder(od)
    deck = deck_values(od)
    summary = {}

    summary["Steel Plate Girders"] = {
        "checks": [(chart, _ur(girder_governing(pg, ids, unit)))
                   for _, chart, ids, unit in GIRDER_CHECKS],
        "note": None if pg else "No plate girder design results.",
    }

    deck_checks = [("Transverse shear", _ur(girder_governing(pg, SLAB_TRANSVERSE_SHEAR_IDS))),
                   ("Crack width", _ur(deck_crack_ratio(deck)))]
    deck_checks += [(chart, _ur(deck_ratio(deck, dk, ck, oh))) for _, chart, dk, ck, _u, oh in DECK_CHECKS]
    summary["Concrete Deck Slab"] = {
        "checks": deck_checks,
        "note": None if deck else "Deck slab design not run.",
    }

    summary["Cross Bracing"] = {
        "checks": [("Compression", _ur(member_governing(bridge, "compression"))),
                   ("Tension", _ur(member_governing(bridge, "tension"))),
                   ("Slenderness", _ur(slenderness_governing(bridge)))],
        "note": None if bridge.has_member_designs() else "No cross-bracing member design.",
    }

    ed = bridge.end_diaphragm()
    if ed.has_member_designs():
        summary["End Diaphragms"] = {
            "checks": [("Compression", _ur(member_governing(ed, "compression"))),
                       ("Tension", _ur(member_governing(ed, "tension")))],
            "note": None,
        }
    else:
        summary["End Diaphragms"] = {"checks": [], "note": "No end-diaphragm member design\n(see Section 5.4)."}
    return summary
