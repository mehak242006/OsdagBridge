"""Matplotlib charts embedded in the report (R4 utilisation ratios, R5 quantities).

Builders return a matplotlib Figure (testable); ``save_chart`` writes it to the
report's temporary assets folder; ``chart_figure_tex`` embeds it with PyLaTeX
``Figure``. Styling comes from ``styles.CHART`` only. Values are plotted as
given - a value of ``None`` is drawn as "n/a", never as zero.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from pylatex import Figure, NoEscape  # noqa: E402

from osdagbridge.core.reports import styles as S  # noqa: E402

C = S.CHART
UR_THRESHOLD = 1.0


def _base_style(ax):
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=C["grid_color"], linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(C["muted_color"])
    ax.tick_params(colors=C["text_color"], labelsize=C["font_size"] - 1)


def _rc():
    return {"font.family": C["font_family"], "font.size": C["font_size"]}


# ═══════════════════════════════════════════════════════════════════════════
# R4 — utilization ratio
# ═══════════════════════════════════════════════════════════════════════════

def ur_bar_panel(ax, title, checks, note=None):
    """One element: bar per check, red dashed threshold at UR = 1.0."""
    _base_style(ax)
    ax.set_title(title, fontsize=C["title_size"], color=C["text_color"], loc="left")
    ax.set_ylabel("Utilization Ratio")
    if not checks:
        ax.set_xticks([])
        ax.text(0.5, 0.5, note or "No data", transform=ax.transAxes, ha="center",
                va="center", color=C["muted_color"], fontsize=C["font_size"])
        ax.set_ylim(0, 1.2)
        ax.axhline(UR_THRESHOLD, color=C["threshold_color"], linestyle=C["threshold_style"],
                   linewidth=C["threshold_width"])
        return ax
    labels = [c[0] for c in checks]
    values = [c[1] for c in checks]
    known = [v for v in values if v is not None]
    top = max(known + [UR_THRESHOLD]) * 1.18
    na_height = top * 0.06
    for i, v in enumerate(values):
        if v is None:
            ax.bar(i, na_height, width=C["bar_width"], color=C["na_color"], hatch="..",
                   edgecolor="white", linewidth=0)
            ax.text(i, na_height, "n/a", ha="center", va="bottom", fontsize=C["font_size"] - 1,
                    color=C["muted_color"])
            continue
        fail = v > UR_THRESHOLD
        ax.bar(i, v, width=C["bar_width"], color=C["fail_color"] if fail else C["pass_color"],
               hatch=C["fail_hatch"] if fail else None, edgecolor="white", linewidth=0)
        ax.text(i, v, f"{v:.2f}" + ("\nFAIL" if fail else ""), ha="center", va="bottom",
                fontsize=C["font_size"] - 1, color=C["text_color"])
    ax.axhline(UR_THRESHOLD, color=C["threshold_color"], linestyle=C["threshold_style"],
               linewidth=C["threshold_width"], zorder=3)
    ax.set_ylim(0, top)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    return ax


def build_ur_figure(summary: dict):
    """2x2 panels (girders, deck, cross bracing, end diaphragms) + shared legend."""
    with plt.rc_context(_rc()):
        fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.6), dpi=C["dpi"])
        for ax, (element, data) in zip(axes.flat, summary.items()):
            ur_bar_panel(ax, element, data["checks"], data.get("note"))
        handles = [
            Patch(facecolor=C["pass_color"], label="Pass (UR ≤ 1.0)"),
            Patch(facecolor=C["fail_color"], hatch=C["fail_hatch"], edgecolor="white",
                  label="Fail (UR > 1.0)"),
            Patch(facecolor=C["na_color"], hatch="..", edgecolor="white", label="Not computed (n/a)"),
            Line2D([0], [0], color=C["threshold_color"], linestyle=C["threshold_style"],
                   linewidth=C["threshold_width"], label="UR = 1.0"),
        ]
        fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
                   fontsize=C["font_size"] - 1)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# R5 — material quantities
# ═══════════════════════════════════════════════════════════════════════════

def _quantity_panel(ax, title, items, unit):
    _base_style(ax)
    ax.set_title(title, fontsize=C["title_size"], color=C["text_color"], loc="left")
    ax.set_ylabel(unit)
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    known = [v for v in values if v is not None] or [1.0]
    top = max(known) * 1.2 or 1.0
    for i, v in enumerate(values):
        if v is None:
            ax.bar(i, top * 0.04, width=C["bar_width"], color=C["na_color"], hatch="..",
                   edgecolor="white", linewidth=0)
            ax.text(i, top * 0.04, "n/a", ha="center", va="bottom",
                    fontsize=C["font_size"] - 1, color=C["muted_color"])
            continue
        ax.bar(i, v, width=C["bar_width"], color=C["series_color"], edgecolor="white", linewidth=0)
        ax.text(i, v, f"{v:,.2f}", ha="center", va="bottom", fontsize=C["font_size"] - 1,
                color=C["text_color"])
    ax.set_ylim(0, top)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    return ax


def build_quantity_figure(steel_items, concrete_m3, rebar_mt):
    """(a) structural steel tonnage by member group; (b) concrete volume and
    (c) reinforcement weight on separate axes, since their units differ."""
    with plt.rc_context(_rc()):
        fig = plt.figure(figsize=(7.4, 3.4), dpi=C["dpi"])
        gs = fig.add_gridspec(1, 4, width_ratios=[2.4, 1, 0.15, 1])
        ax_s = fig.add_subplot(gs[0, 0])
        ax_c = fig.add_subplot(gs[0, 1])
        ax_r = fig.add_subplot(gs[0, 3])
        _quantity_panel(ax_s, "(a) Structural steel", steel_items, "Weight (MT)")
        _quantity_panel(ax_c, "(b) Concrete", [("Deck slab", concrete_m3)], "Volume (m³)")
        _quantity_panel(ax_r, "(c) Reinforcement", [("Deck slab", rebar_mt)], "Weight (MT)")
        fig.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# Saving and embedding
# ═══════════════════════════════════════════════════════════════════════════

def save_chart(fig, directory, name):
    """Write ``fig`` as PNG into ``directory`` (the report's temporary assets)."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name + ".png")
    fig.savefig(path, dpi=C["dpi"], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def chart_figure_tex(path, caption, label=None):
    """PyLaTeX Figure embedding a saved chart."""
    fig = Figure(position="H")
    fig.add_image(path.replace("\\", "/"), width=NoEscape(S.FIGURE["chart_width"]))
    fig.add_caption(NoEscape(caption))
    if label:
        fig.append(NoEscape(r"\label{" + label + "}"))
    return fig.dumps()
