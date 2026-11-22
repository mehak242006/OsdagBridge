"""R1 — multi-page tables repeat their column header on every page."""
import pathlib
import re
import shutil
import subprocess

import pytest

from osdagbridge.core.reports import styles as S
from osdagbridge.core.reports.report_generator import preamble
from osdagbridge.core.reports.report_utils import count_columns, longtable_begin

REPORTS_DIR = pathlib.Path(S.__file__).parent
HEADER = r"\textbf{Girder} & \textbf{Check} & \textbf{UR} \\[\osdagRowPad]"


@pytest.mark.parametrize("spec, n", [
    (r"|L{5.5cm}|p{10.0cm}|", 2),
    (r"|C{2.5cm}|C{3.5cm}|C{3.5cm}|>{\centering\arraybackslash}p{4.2cm}|C{1.8cm}|", 5),
    (r"|l|c|r|", 3),
    (r"@{}l@{\hspace{2pt}}r@{}", 2),
])
def test_count_columns(spec, n):
    assert count_columns(spec) == n


def test_count_columns_rejects_empty_spec():
    with pytest.raises(ValueError):
        count_columns("||")


def test_longtable_begin_defines_all_header_sections():
    tex = longtable_begin(r"|l|c|r|", HEADER, caption=r"\textbf{Demo}")
    for marker in (r"\endfirsthead", r"\endhead", r"\endfoot", r"\endlastfoot"):
        assert tex.count(marker) == 1, marker
    first, rest = tex.split(r"\endfirsthead")
    head = rest.split(r"\endhead")[0]
    # header row appears on the first page AND in the repeated head
    assert HEADER in first and HEADER in head
    # caption is terminated with \\ (otherwise longtable raises "Misplaced \noalign")
    assert r"\caption{\textbf{Demo}}\\" in first
    assert r"\caption[]{\textbf{Demo} " + S.TABLE_CONTINUED_SUFFIX + r"}\\" in head
    # continuation note spans every column
    assert r"\multicolumn{3}{r}" in tex
    assert tex.endswith("\\endlastfoot\n")


def test_longtable_begin_without_caption_still_repeats_header():
    tex = longtable_begin(r"|l|l|", r"A & B \\")
    assert r"\caption" not in tex
    assert tex.count("A & B") == 2


def test_header_shading_uses_style_colour():
    assert r"\rowcolor{osdagTableHeader}" in longtable_begin("|l|", r"X \\")
    assert r"\rowcolor" not in longtable_begin("|l|", r"X \\", shade=False)


def _longtable_blocks(src):
    return re.findall(r"\\begin\{longtable\}.*?\\end\{longtable\}", src, flags=re.S)


@pytest.mark.parametrize("module", sorted(REPORTS_DIR.glob("chap*.py")), ids=lambda p: p.name)
def test_every_handwritten_longtable_repeats_its_header(module):
    """Any longtable not built with longtable_begin() must define its own repeated head."""
    src = module.read_text(encoding="utf-8")
    for block in _longtable_blocks(src):
        assert r"\endfirsthead" in block and r"\endhead" in block, block[:120]
        head = block.split(r"\endfirsthead")[1].split(r"\endhead")[0]
        assert r"\textbf" in head, "repeated head is empty: " + block[:120]


# ── integration: compile a 3-page table and check every page carries the header ──

def _pdflatex():
    try:
        from osdag_latex_env.__main__ import OsdagLatexEnv
        exe = OsdagLatexEnv().pdflatex
        if exe:
            return str(exe)
    except Exception:
        pass
    return shutil.which("pdflatex")


@pytest.mark.skipif(not (_pdflatex() and shutil.which("pdftotext")),
                    reason="needs pdflatex and pdftotext")
def test_compiled_table_repeats_header_on_every_page(tmp_path):
    rows = "\n".join(rf"G{i} & Check {i} & 0.{i % 10}0 \\[\osdagRowPad]" + "\n\\hline" for i in range(120))
    doc = (preamble("P", "J", "2026-01-01")
           + longtable_begin(r"|C{3cm}|L{6cm}|C{3cm}|", HEADER, caption=r"\textbf{Repeat Test}")
           + rows + "\n\\end{longtable}\n\\end{document}\n")
    (tmp_path / "t.tex").write_text(doc, encoding="utf-8")
    for _ in range(2):
        subprocess.run([_pdflatex(), "-interaction=nonstopmode", "t.tex"], cwd=tmp_path,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    log = (tmp_path / "t.log").read_text(encoding="latin-1")
    assert not re.search(r"^! ", log, flags=re.M), "LaTeX errors in log"
    text = subprocess.run(["pdftotext", "-raw", str(tmp_path / "t.pdf"), "-"],
                          stdout=subprocess.PIPE, check=True).stdout.decode("utf-8", "ignore")
    pages = [p for p in text.split("\f") if "G" in p]
    assert len(pages) >= 3
    for i, page in enumerate(pages):
        assert "Girder Check UR" in page, f"header missing on table page {i + 1}"
        if i > 0:
            assert "(continued)" in page
        if i < len(pages) - 1:
            assert "Continued on next page" in page
