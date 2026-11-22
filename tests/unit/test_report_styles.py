"""R6 — centralised report formatting (styles.py is the single source of truth)."""
import pathlib
import re

import pytest

from osdagbridge.core.reports import styles as S
from osdagbridge.core.reports.report_generator import preamble

REPORTS_DIR = pathlib.Path(S.__file__).parent
CHAPTER_MODULES = sorted(
    p for p in REPORTS_DIR.glob("*.py")
    if p.name not in {"styles.py", "__init__.py"}
)

# Literal formatting values that must not appear outside styles.py.
FORBIDDEN = {
    "row padding literal": re.compile(r"\\\\\[-?[0-9.]+(pt|em|cm)\]"),
    "vspace literal": re.compile(r"\\vspace\*?\{-?[0-9.]+(pt|em|cm)\}"),
    "named colour": re.compile(r"\\textcolor\{\{?(red|black|blue|green|gray)\b"),
    "colour definition": re.compile(r"\\definecolor"),
    "tabcolsep literal": re.compile(r"\\tabcolsep\}\{[0-9]"),
    "arraystretch literal": re.compile(r"\\arraystretch\}\{[0-9]"),
    "font size command": re.compile(r"\\(tiny|scriptsize|footnotesize|small|large|Large|LARGE|huge|Huge)(?![A-Za-z])"),
    "geometry literal": re.compile(r"\\usepackage\[[^\]]*margin="),
}


def test_required_sections_exist():
    for name in ("PAGE_GEOMETRY", "COLORS", "FONT_SIZES", "TABLE", "LENGTHS",
                 "HEADER_FOOTER", "HEADINGS", "FIGURE", "CHART"):
        assert getattr(S, name), name
    for colour in ("osdagGreen", "osdagPass", "osdagFail"):
        assert re.fullmatch(r"[0-9A-Fa-f]{6}", S.COLORS[colour])
    assert "osdagRowPad" in S.LENGTHS


def test_style_block_defines_every_colour_and_length():
    block = S.latex_style_definitions()
    for name, hex_code in S.COLORS.items():
        assert rf"\definecolor{{{name}}}{{HTML}}{{{hex_code}}}" in block
    for name, value in S.LENGTHS.items():
        assert rf"\setlength{{\{name}}}{{{value}}}" in block


@pytest.mark.parametrize("module", CHAPTER_MODULES, ids=lambda p: p.name)
def test_no_formatting_literals_outside_styles(module):
    src = module.read_text(encoding="utf-8")
    hits = [f"{label}: {m.group(0)}" for label, rx in FORBIDDEN.items() for m in rx.finditer(src)]
    assert not hits, f"{module.name} has hard-coded formatting: {hits}"


def test_changing_a_colour_changes_the_preamble(monkeypatch):
    monkeypatch.setitem(S.COLORS, "osdagFail", "123ABC")
    tex = preamble("P", "J", "2026-01-01")
    assert r"\definecolor{osdagFail}{HTML}{123ABC}" in tex


def test_changing_row_padding_and_margins_changes_the_preamble(monkeypatch):
    monkeypatch.setitem(S.LENGTHS, "osdagRowPad", "9pt")
    monkeypatch.setitem(S.PAGE_GEOMETRY, "margin", "2cm")
    tex = preamble("P", "J", "2026-01-01")
    assert r"\setlength{\osdagRowPad}{9pt}" in tex
    assert "margin=2cm" in tex


def test_header_footer_theme_comes_from_styles(monkeypatch):
    monkeypatch.setitem(S.HEADER_FOOTER, "rule_thickness", "2.5pt")
    tex = preamble("P", "J", "2026-01-01")
    assert "height 2.5pt" in tex
    assert S.HEADER_FOOTER["footer_left"] in tex
