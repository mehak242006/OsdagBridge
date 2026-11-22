"""Centralised formatting for the OsdagBridge design report.

This module is the single source of truth for every visual/layout attribute of
the generated PDF: page geometry, fonts, colours, table styling, header/footer
theme, figure sizes and chart styling.

How it is consumed
------------------
* ``report_generator.preamble()`` calls :func:`latex_style_definitions` which
  turns the values below into LaTeX colour definitions (``\\definecolor``) and
  length registers (``\\newlength``/``\\setlength``).
* Chapter modules never contain literal sizes or colours; they reference the
  semantic names defined here, e.g. ``\\\\[\\osdagRowPad]`` to end a table row
  or ``\\textcolor{osdagFail}{FAIL}``. Changing a value here therefore changes
  every table/figure in the report.
* Python-side helpers (tables in ``report_utils``, charts in ``charts``) import
  the constants directly.

Only *presentation* lives here. Engineering values never do.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# 1. Document & page geometry
# ═══════════════════════════════════════════════════════════════════════════
DOCUMENT_CLASS = "report"
PAPER = "a4paper"
BASE_FONT_SIZE = "12pt"
LINE_STRETCH = 1.15              # \setstretch
# Extra stretch TeX may use before letting a line (or a narrow table cell)
# run past its box: avoids over-wide lines with long codes such as
# "IRC 6:2017 Cl.208.2/208.3".
EMERGENCY_STRETCH = "3em"

# Options passed to \usepackage[...]{geometry}.
# * left/right 20 mm: 170 mm text width so the report's wide tables fit
#   inside the printable area (with 1in they overflowed the right margin).
# * headheight 18pt: fancyhdr needs >= 17.5pt for the two-part header;
#   with the default 12pt the header box overflowed on every page.
# * footskip 14mm: places the footer (and the "* Software default value"
#   note drawn just above the footer rule) clear of the last text line.
# * top/bottom 1in keep the text block ending at y = 770pt on A4.
PAGE_GEOMETRY = {
    "top":        "1in",
    "bottom":     "1in",
    "left":       "20mm",
    "right":      "20mm",
    "headheight": "18pt",
    "footskip":   "14mm",
}
PAPER_WIDTH_MM = 210.0

PT_PER_CM = 72.27 / 2.54


def _to_cm(length: str) -> float:
    """Convert '20mm' / '1in' / '2.5cm' / '6pt' to centimetres."""
    for unit, factor in (("mm", 0.1), ("cm", 1.0), ("in", 2.54), ("pt", 1 / PT_PER_CM)):
        if length.endswith(unit):
            return float(length[: -len(unit)]) * factor
    raise ValueError(f"unsupported length {length!r}")


def text_width_cm() -> float:
    """Width of the text block implied by PAGE_GEOMETRY."""
    return (PAPER_WIDTH_MM / 10.0
            - _to_cm(PAGE_GEOMETRY["left"]) - _to_cm(PAGE_GEOMETRY["right"]))

# ═══════════════════════════════════════════════════════════════════════════
# 2. Colour palette  (name -> HTML hex)
#    Every colour used in the report is defined from this dict.
# ═══════════════════════════════════════════════════════════════════════════
COLORS = {
    "osdagGreen":   "91B014",   # brand colour: header/footer rules, info log lines
    "osdagPass":    "000000",   # PASS status text
    "osdagFail":    "FF0000",   # FAIL status text / UR > 1.0
    "osdagWarning": "0000FF",   # warning lines in the design log
    "osdagError":   "FF0000",   # error lines in the design log
    "osdagText":    "000000",   # neutral text (software-default footnote)
    "osdagTableHeader": "EEF3DC",  # light tint of osdagGreen behind table header rows
}

# Text appended to a table caption on continuation pages, and the note printed
# at the bottom of a page where a table continues.
TABLE_CONTINUED_SUFFIX = r"\textit{(continued)}"
TABLE_CONTINUES_NOTE = r"\textit{Continued on next page}"

# ═══════════════════════════════════════════════════════════════════════════
# 3. Typography
# ═══════════════════════════════════════════════════════════════════════════
FONT_SIZES = {
    "title_main":     r"\Huge",        # "OsdagBridge" on the title page
    "title_subtitle": r"\large",       # tagline on the title page
    "title_report":   r"\Large",       # "Design Report" on the title page
    "chapter":        r"\Large",       # chapter headings and TOC title
    "footnote":       r"\footnotesize",  # software-default footnote
    "dense_table":    r"\footnotesize",  # very wide tables (Table 4.1)
    "caption":        r"\small",       # unnumbered figure captions
}

# Chapter headings and table of contents (titlesec / titletoc)
HEADINGS = {
    "chapter_label_sep":     "1em",    # gap between chapter number and title
    "chapter_before_toc":    "0pt",    # space above the TOC heading
    "chapter_before":        "-30pt",  # space above numbered chapter headings
    "chapter_after":         "10pt",   # space below chapter headings
    "toc_tocdepth":          2,
    # (left indent, number-label width) per TOC level
    "toc_chapter":           ("1.5em", "1.5em"),
    "toc_section":           ("3.8em", "2.3em"),
    "toc_subsection":        ("7.0em", "3.2em"),
}

# ═══════════════════════════════════════════════════════════════════════════
# 4. Tables
# ═══════════════════════════════════════════════════════════════════════════
TABLE = {
    "tabcolsep":       "6pt",
    "arraystretch":    1.12,
    "arraystretch_dense": 1.25,    # wide multi-column tables (Table 4.1)
    "lt_pre":          "0pt",      # \LTpre  (space before a longtable)
    "lt_post":         "6pt",      # \LTpost (space after a longtable)
    "rule_width":      "0.5pt",    # \arrayrulewidth
    "extra_row_height": "0.6pt",   # \extrarowheight
    "needspace_lines": 5,          # min. free lines before a table starts
    # longtable typesets rows in chunks of \LTchunksize (default 20); at a
    # chunk boundary the "no page break" request of \\* is dropped, so a
    # row group could still be split. A chunk larger than any report table
    # removes those boundaries.
    "lt_chunk_size":   1000,
}

# Repeated column specification of the two-column "parameter | value" tables.
PARAM_VALUE_COLSPEC = r"|L{5.5cm}|p{10.0cm}|"

# Executive-summary "Final Bridge Geometry" table: one label column plus one
# equal-width column per girder sharing the remaining width.
EXEC_GEOMETRY_TABLE = {
    "label_col_cm":       2.8,
    "min_girder_col_cm":  1.5,
    "info_colspec":       r"|L{5.5cm}|L{8.5cm}|",
}

# ═══════════════════════════════════════════════════════════════════════════
# 5. Named lengths
#    Emitted as \newlength{\<name>} + \setlength; chapters reference the name.
# ═══════════════════════════════════════════════════════════════════════════
LENGTHS = {
    # table row padding (used as  \\[\osdagRowPad])
    "osdagRowPad":        "6pt",
    "osdagRowPadLarge":   "8pt",
    "osdagRowPadSmall":   "3pt",
    # column separation overrides for wide tables
    "osdagColSepCompact": "4pt",
    "osdagColSepTight":   "3.5pt",
    "osdagColSepDense":   "3pt",
    # vertical rhythm
    "osdagBlockSkip":     "1em",    # gap before a table / block
    "osdagTightSkip":     "0.4em",  # small gap (between note and table, etc.)
    "osdagNoteSkip":      "0.3em",  # gap before a table footnote
    "osdagMinorSkip":     "0.6em",
    "osdagMediumSkip":    "0.8em",
    "osdagWideSkip":      "2.2em",
    "osdagParaSkip":      "0.4cm",
    "osdagIntroSkip":     "0.5cm",
    "osdagSectionSkip":   "0.8cm",
    "osdagCaptionSkip":   "4pt",    # gap between a sub-table and its caption
    "osdagFigureSkip":    "0.5em",  # trim above/below embedded figures
    "osdagTocSkip":       "2pt",    # gap before each chapter line in the TOC
    "osdagCaptionGap":    "2pt",    # \abovecaptionskip / \belowcaptionskip
    # space reserved for a table caption on top of the measured head + first
    # row when deciding whether a longtable may start on the current page
    "osdagCaptionAllowance": "3\\baselineskip",
}

# Font-role macros (emitted as \newcommand{\<name>}{<size>}).
FONT_MACROS = {
    "osdagDenseTableFont": FONT_SIZES["dense_table"],
    "osdagFootnoteFont":   FONT_SIZES["footnote"],
    "osdagChapterFont":    FONT_SIZES["chapter"],
    "osdagCaptionFont":    FONT_SIZES["caption"],
}

# ═══════════════════════════════════════════════════════════════════════════
# 6. Header / footer theme
# ═══════════════════════════════════════════════════════════════════════════
HEADER_FOOTER = {
    "rule_color":        "osdagGreen",
    "rule_thickness":    "1pt",
    "head_rule_gap":     "2pt",     # gap below the header rule
    "foot_rule_gap":     "6pt",     # gap below the footer rule
    "foot_rule_raise":   "-8pt",    # footer rule offset (no software-default note)
    "sd_note_raise":     "-20pt",   # offset of the software-default note
    "sd_note_gap":       "4pt",     # gap between the note and the footer rule
    "footer_left":       r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay",
    "sd_note_text":      r"* Software default value",
}

# ═══════════════════════════════════════════════════════════════════════════
# 7. Title page
# ═══════════════════════════════════════════════════════════════════════════
TITLE_PAGE = {
    "top_skip":       "1.5cm",
    "logo_gap":       "1cm",
    "tagline_gap":    "0.3cm",
    "block_gap":      "1.5cm",
    "logo_height":    "2.2cm",
    "meta_colspec":   r"|L{4cm}|L{10cm}|",
}

# ═══════════════════════════════════════════════════════════════════════════
# 8. Figures embedded in the PDF
# ═══════════════════════════════════════════════════════════════════════════
FIGURE = {
    "default_width":  r"0.9\textwidth",
    "full_width":     r"\textwidth",
    "drawing_width":  r"0.85\textwidth",
    "chart_width":    r"0.95\textwidth",
    "placeholder_width": r"0.97\textwidth",
}

# ═══════════════════════════════════════════════════════════════════════════
# 9. Matplotlib charts (utilisation ratio / material quantity)
# ═══════════════════════════════════════════════════════════════════════════
CHART = {
    "dpi":             200,
    "figsize":         (7.0, 3.6),       # inches, single chart
    "font_family":     "DejaVu Sans",
    "font_size":       9,
    "title_size":      10,
    "pass_color":      "#91B014",        # osdagGreen
    "fail_color":      "#D62728",
    "na_color":        "#BDBDBD",
    "threshold_color": "red",
    "threshold_style": "--",
    "threshold_width": 1.4,
    "bar_edge_color":  "#333333",
    "grid_color":      "#DDDDDD",
    "steel_color":     "#4C72B0",
    "concrete_color":  "#8C8C8C",
    "rebar_color":     "#C44E52",
}


# ═══════════════════════════════════════════════════════════════════════════
# Helpers that turn the configuration into LaTeX
# ═══════════════════════════════════════════════════════════════════════════

def geometry_options() -> str:
    """Option string for ``\\usepackage[...]{geometry}``."""
    opts = [PAPER] + [f"{k}={v}" for k, v in PAGE_GEOMETRY.items()]
    return ", ".join(opts)


def latex_style_definitions() -> str:
    """LaTeX preamble block: colours, named lengths and global table settings."""
    lines = ["% --- Generated from osdagbridge.core.reports.styles ---"]
    for name, hex_code in COLORS.items():
        lines.append(rf"\definecolor{{{name}}}{{HTML}}{{{hex_code}}}")
    for name, value in LENGTHS.items():
        lines.append(rf"\newlength{{\{name}}}\setlength{{\{name}}}{{{value}}}")
    for name, value in FONT_MACROS.items():
        lines.append(rf"\newcommand{{\{name}}}{{{value}}}")
    t = TABLE
    lines.append(rf"\newcommand{{\osdagDenseArrayStretch}}{{{t['arraystretch_dense']}}}")
    lines.append(rf"\setlength{{\emergencystretch}}{{{EMERGENCY_STRETCH}}}")
    lines.append(r"\newsavebox{\osdagProbeBox}")   # used by keep_table_starts_together()
    lines += [
        rf"\setlength{{\tabcolsep}}{{{t['tabcolsep']}}}",
        rf"\renewcommand{{\arraystretch}}{{{t['arraystretch']}}}",
        rf"\setlength{{\LTpre}}{{{t['lt_pre']}}}",
        rf"\setlength{{\LTpost}}{{{t['lt_post']}}}",
        rf"\setcounter{{LTchunksize}}{{{t['lt_chunk_size']}}}",
        rf"\setlength{{\arrayrulewidth}}{{{t['rule_width']}}}",
        rf"\setlength{{\extrarowheight}}{{{t['extra_row_height']}}}",
        rf"\BeforeBeginEnvironment{{table}}{{\needspace{{{t['needspace_lines']}\baselineskip}}}}",
        # No soft \needspace before longtables: its cheap (-100) breakpoint is
        # chosen only after longtable has installed its output routine, which
        # then prints an orphan foot and a doubled head. Longtables get an
        # exact, hard check from report_utils.keep_table_starts_together().
    ]
    return "\n".join(lines) + "\n"


def footrule_definition(with_sd_note_support: bool = True) -> str:
    """``\\renewcommand{\\footrule}`` body for the main/plain page styles."""
    hf = HEADER_FOOTER
    rule = (rf"\color{{{hf['rule_color']}}}\hrule width\headwidth "
            rf"height {hf['rule_thickness']} \vspace{{{hf['foot_rule_gap']}}}%")
    if not with_sd_note_support:
        return rf"\renewcommand{{\footrule}}{{\vspace{{{hf['foot_rule_raise']}}}" + rule.rstrip('%') + "}"
    return (
        r"\renewcommand{\footrule}{%" + "\n"
        r"    \ifbool{hasSDonPage}{%" + "\n"
        rf"      \vspace{{{hf['sd_note_raise']}}}%" + "\n"
        rf"      \hbox to \headwidth{{\textcolor{{osdagText}}{{{FONT_SIZES['footnote']}\textit{{{hf['sd_note_text']}}}}}\hfil}}%" + "\n"
        rf"      \vspace{{{hf['sd_note_gap']}}}%" + "\n"
        r"    }{%" + "\n"
        rf"      \vspace{{{hf['foot_rule_raise']}}}%" + "\n"
        r"    }%" + "\n"
        rf"    {rule}" + "\n"
        r"  }"
    )


def chapter_heading_format(before: str) -> str:
    """``\\titleformat`` + ``\\titlespacing`` for chapters (``before`` = space above)."""
    h = HEADINGS
    return (rf"\titleformat{{\chapter}}[block]{{\normalfont{FONT_SIZES['chapter']}\bfseries\centering}}"
            rf"{{\thechapter}}{{{h['chapter_label_sep']}}}{{}}" + "\n"
            rf"\titlespacing*{{\chapter}}{{0pt}}{{{before}}}{{{h['chapter_after']}}}")


def toc_entry_formats() -> str:
    """``\\titlecontents`` definitions for chapter/section/subsection TOC lines."""
    h = HEADINGS
    out = []
    for level in ("chapter", "section", "subsection"):
        indent, label = h[f"toc_{level}"]
        above = r"\normalfont\vspace{\osdagTocSkip}" if level == "chapter" else r"\normalfont"
        out.append(
            rf"\titlecontents{{{level}}}[{indent}]" + "\n"
            rf"  {{{above}}}" + "\n"
            rf"  {{\contentslabel{{{label}}}}}" + "\n"
            rf"  {{\hspace*{{-{label}}}}}" + "\n"
            r"  {\hfill\contentspage}")
    return "\n\n".join(out)


def headrule_definition() -> str:
    hf = HEADER_FOOTER
    return (rf"\renewcommand{{\headrule}}{{\color{{{hf['rule_color']}}}\hrule width\headwidth "
            rf"height {hf['rule_thickness']} \vspace{{{hf['head_rule_gap']}}}}}")
