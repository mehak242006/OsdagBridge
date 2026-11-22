"""R2 — layout: no content in the footer, tables inside the printable area."""
import re
import shutil
import subprocess

import pytest

from osdagbridge.core.reports import styles as S
from osdagbridge.core.reports.report_generator import preamble, title_page, ReportMetadata
from osdagbridge.core.reports.report_utils import (
    count_columns, fit_colspec, keep_row_groups_together, longtable_begin,
)


# ── row groups ────────────────────────────────────────────────────────────

GROUP = (r"\multirow{3}{*}{\makecell{G1}} & a & 1 \\[\osdagRowPad]" "\n"
         r"\cline{2-3}" "\n"
         r" & \makecell{line\\break} & 2 \\[\osdagRowPad]" "\n"
         r"\cline{2-3}" "\n"
         r" & c & 3 \\[\osdagRowPad]" "\n"
         r"\hline" "\n"
         r"G2 & d & 4 \\[\osdagRowPad]" "\n"
         r"\hline")


def test_group_rows_are_bound_except_the_last():
    out = keep_row_groups_together(GROUP)
    row_ends = re.findall(r"\\\\\*?\[\\osdagRowPad\]", out)
    assert row_ends == [r"\\*[\osdagRowPad]", r"\\*[\osdagRowPad]",
                        r"\\[\osdagRowPad]", r"\\[\osdagRowPad]"]
    # line break inside \makecell is not a row end and stays untouched
    assert r"\makecell{line\\break}" in out


def test_hline_separated_multirow_group_is_bound():
    tex = (r"\multirow{2}{*}{P1} & x \\" "\n" r"\hline" "\n"
           r" & y \\" "\n" r"\hline")
    assert keep_row_groups_together(tex).count(r"\\*") == 1


def test_keep_row_groups_together_is_idempotent():
    once = keep_row_groups_together(GROUP)
    assert keep_row_groups_together(once) == once


# ── table width ───────────────────────────────────────────────────────────

def _total_width_cm(spec):
    widths = sum(float(w) for w in re.findall(r"[LCRpmb]\{([0-9.]+)cm\}", spec))
    n = count_columns(spec)
    return (widths + n * 2 * S._to_cm(S.TABLE["tabcolsep"])
            + (n + 1) * S._to_cm(S.TABLE["rule_width"]))


def test_fit_colspec_scales_wide_tables_into_text_width():
    wide = r"|C{2.0cm}|L{1.8cm}|C{2.2cm}|C{3.0cm}|C{1.8cm}|C{1.8cm}|C{1.2cm}|C{1.8cm}|"
    assert _total_width_cm(wide) > S.text_width_cm()
    fitted = fit_colspec(wide)
    assert _total_width_cm(fitted) <= S.text_width_cm() + 1e-6
    assert count_columns(fitted) == count_columns(wide)


def test_fit_colspec_keeps_fitting_specs_and_modifiers():
    spec = r"|L{3cm}|>{\centering\arraybackslash}p{4cm}|"
    assert fit_colspec(spec) == spec
    narrow = fit_colspec(r"|L{20cm}|>{\centering\arraybackslash}p{20cm}|")
    assert r">{\centering\arraybackslash}p{" in narrow


def test_page_geometry_settings():
    assert S._to_cm(S.PAGE_GEOMETRY["headheight"]) >= S._to_cm("17.5pt")  # fancyhdr minimum
    assert "footskip" in S.PAGE_GEOMETRY
    assert abs(S.text_width_cm() - 17.0) < 1e-9
    opts = S.geometry_options()
    for k in ("headheight", "footskip", "left", "right"):
        assert k + "=" in opts


def test_page_counter_continues_after_title_page():
    md = ReportMetadata(project_name="P", project_location="L", designer="D",
                        client="C", company="O")
    tex = title_page(md, None, None)
    assert tex.index(r"\end{titlepage}") < tex.index(r"\setcounter{page}{2}")


# ── integration: a group straddling a page break moves as a whole ─────────

def _pdflatex():
    try:
        from osdag_latex_env.__main__ import OsdagLatexEnv
        exe = OsdagLatexEnv().pdflatex
        if exe:
            return str(exe)
    except Exception:
        pass
    return shutil.which("pdflatex")


A4_TEXT_BOTTOM_PT = 842 - 72      # 1in bottom margin on A4
DESCENDER_ALLOWANCE_PT = 6


@pytest.mark.skipif(not (_pdflatex() and shutil.which("pdftotext")),
                    reason="needs pdflatex and pdftotext")
@pytest.mark.parametrize("filler_lines", [28, 31, 34])
def test_compiled_groups_never_split_or_enter_footer(tmp_path, filler_lines):
    rows = []
    for g in range(1, 7):
        rows.append(rf"\multirow{{6}}{{*}}{{\makecell{{G{g}}}}} & G{g}-row1 & v \\[\osdagRowPad]")
        for r in range(2, 7):
            rows.append(r"\cline{2-3}")
            rows.append(rf" & G{g}-row{r} & v \\[\osdagRowPad]")
        rows.append(r"\hline")
    filler = "\n\n".join(f"Filler paragraph {i}." for i in range(filler_lines))
    body = (filler + "\n\n"
            + longtable_begin(r"|C{2.5cm}|L{6cm}|C{3cm}|",
                              r"\textbf{Girder} & \textbf{Parameter} & \textbf{Value} \\",
                              caption=r"\textbf{Group test}")
            + "\n".join(rows) + "\n\\end{longtable}\n")
    doc = preamble("P", "J", "2026-01-01") + keep_row_groups_together(body) + "\\end{document}\n"
    (tmp_path / "t.tex").write_text(doc, encoding="utf-8")
    for _ in range(2):
        subprocess.run([_pdflatex(), "-interaction=nonstopmode", "t.tex"], cwd=tmp_path,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert not re.search(r"^! ", (tmp_path / "t.log").read_text(encoding="latin-1"), flags=re.M)
    pdf = str(tmp_path / "t.pdf")
    pages = subprocess.run(["pdftotext", "-raw", pdf, "-"], stdout=subprocess.PIPE,
                           check=True).stdout.decode("utf-8", "ignore").split("\f")
    for g in range(1, 7):
        on = [i for i, p in enumerate(pages) if f"G{g}-row" in p]
        assert len(set(on)) == 1, f"group G{g} split over pages {on}"
        page = pages[on[0]]
        assert all(f"G{g}-row{r}" in page for r in range(1, 7))
        assert re.search(rf"(^|\s)G{g}(\s|$)", page), f"label G{g} not on its rows' page"
    for i in range(1, len(pages)):
        band = subprocess.run(
            ["pdftotext", "-layout", "-f", str(i), "-l", str(i), "-margint",
             str(A4_TEXT_BOTTOM_PT + DESCENDER_ALLOWANCE_PT), pdf, "-"],
            stdout=subprocess.PIPE, check=True).stdout.decode("utf-8", "ignore")
        stray = [ln for ln in band.splitlines()
                 if ln.strip() and "Osdag | FOSSEE" not in ln and "Page " not in ln]
        assert not stray, f"text in footer band on page {i}: {stray}"
