from osdagbridge.core.reports.report_utils import longtable_begin


def _mt(input_dict, key):
    """Value of a Table 7.1 entry as a float, or None when the BOQ did not compute it ('N.A.')."""
    try:
        return float(str(input_dict.get(key)).replace(',', ''))
    except (TypeError, ValueError):
        return None


def quantity_chart_data(input_dict):
    """Chart values taken from the same keys as Table 7.1 (nothing is recalculated).

    Returns (steel_items, concrete_m3, rebar_mt). Steel is in MT per member group;
    cross bracing is the sum of its top, bottom and diagonal chords. The BOQ has no
    end-diaphragm quantity, so that bar is None and drawn as 'n/a'.
    """
    girders = _mt(input_dict, 'steel_girders_wt_total')
    parts = [_mt(input_dict, k) for k in ('bracing_top_wt_total', 'bracing_bot_wt_total', 'bracing_diag_wt_total')]
    bracing = sum(parts) if all(v is not None for v in parts) else None
    steel_items = [('Girders', girders), ('Cross bracing', bracing), ('End diaphragms', None)]
    return steel_items, _mt(input_dict, 'concrete_deck_vol_total'), _mt(input_dict, 'rebar_deck_wt_total')


def _quantity_chart_tex(input_dict, chart_dir):
    """R5: bar charts of the Table 7.1 quantities, saved to the temporary assets folder."""
    if not chart_dir:
        return ''
    import logging, os
    from osdagbridge.core.reports.charts import build_quantity_figure, chart_figure_tex, save_chart
    steel_items, concrete, rebar = quantity_chart_data(input_dict)
    if all(v is None for _, v in steel_items) and concrete is None and rebar is None:
        return ''
    try:
        save_chart(build_quantity_figure(steel_items, concrete, rebar), chart_dir, 'quantities')
    except Exception as exc:                       # never break the report for a chart
        logging.getLogger(__name__).warning('Quantity chart not generated: %s', exc)
        return r'\noindent\textit{Quantity chart could not be generated.}'
    return chart_figure_tex(
        os.path.basename(chart_dir) + '/quantities.png',
        'Material quantities from Table~7.1: (a) structural steel by member group (MT; no end-diaphragm '
        'quantity is computed by OsdagBridge), (b) concrete volume (m' + chr(36) + '^3' + chr(36) + '), (c) reinforcement steel weight (MT)',
        label='fig:quantities')


def ch7_quantities(input_dict, chart_dir=None):
    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

\begingroup
\setlength{\tabcolsep}{\osdagColSepTight}
""" + longtable_begin(r"|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|",
    r"\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume} & \textbf{Quantity} & \textbf{Total Volume} & \textbf{Weight (MT)} & \textbf{Total Weight (MT)} \\",
    caption=r"\textbf{Bill of Materials (Steel, Concrete, and Reinforcement Quantities)}",
    label="tab:bom") + r"""1 &Structural Steel (IS 2062) for Girders & """ + str(input_dict.get("steel_girders_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_qty", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_wt_total", "N.A.")) + r""" \\
\hline
2(a) & Cross Bracing - Top Chord & """ + str(input_dict.get("bracing_top_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_qty", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_wt_total", "N.A.")) + r""" \\
\hline
2(b) & Cross Bracing - Bottom Chord & """ + str(input_dict.get("bracing_bot_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_qty", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_wt_total", "N.A.")) + r""" \\
\hline
2(c) & Cross Bracing - Diagonal Chord & """ + str(input_dict.get("bracing_diag_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_qty", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_wt_total", "N.A.")) + r""" \\
\hline
3 & Concrete (M40) for Deck Slab & """ + str(input_dict.get("concrete_deck_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_qty", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_wt_total", "N.A.")) + r""" \\
\hline
4 & Reinforcement Steel (Fe 500) & """ + str(input_dict.get("rebar_deck_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_qty", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_wt_total", "N.A.")) + r""" \\
\hline
5 & Shear Stud Connectors & """ + str(input_dict.get("shear_studs_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_qty", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_wt_total", "N.A.")) + r""" \\
\hline
6 & Crash Barrier & """ + str(input_dict.get("crash_barrier_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_qty", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_wt_total", "N.A.")) + r""" \\
\hline
\end{longtable}
\endgroup
""" + _quantity_chart_tex(input_dict, chart_dir) + "\n"


