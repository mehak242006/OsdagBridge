import re

from osdagbridge.core.reports import styles as S
from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_DEPTH,
    KEY_TS_NO_OF_GIRDERS
)


def _tex(value):
    """Escape a Python value for safe LaTeX embedding."""
    s = str(value) if value is not None else ''
    if not s:
        return r''
    # Normalise non-ASCII glyphs from section designations (e.g. "∠ 100 ⅹ 100ⅹ 10")
    # that pdflatex cannot render.
    for uni, ascii_ in [('∠', 'L'), ('ⅹ', 'x'), ('×', 'x')]:
        s = s.replace(uni, ascii_)
    s = s.replace('\\', r'\textbackslash{}')
    for ch, esc in [('&', r'\&'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'),
                    ('{', r'\{'), ('}', r'\}'),          
                    ('_', r'\_\allowbreak{}'),            
                    ('~', r'\textasciitilde{}'), ('^', r'\^{}')]:
        s = s.replace(ch, esc)
    s = s.replace(':', r':\allowbreak{}')
    # Math relations in check names (e.g. "Leg ≤ H_limit"): typeset as math
    # symbols. Done after escaping so the inserted macros are not escaped.
    for uni, macro in [('≤', r'\ensuremath{\leq}'), ('≥', r'\ensuremath{\geq}')]:
        s = s.replace(uni, macro)
    return s


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val in ("", None):
        return ""
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """
    Retrieve all girder labels and member IDs from backend keys.

    Usage Example:
    --------------------------
    girder_entries = get_girder_entries(bridge.input_dict)
    
    # 1. Fallback handling (if backend hasn't populated keys yet)
    if not girder_entries:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1))
        girder_entries = [(f"Girder {i}", f"M1") for i in range(1, n + 1)]
        
    # 2. Get total number of girders safely
    n_girders = len(girder_entries)
    
    # 3. Iterate over the girders to build table rows
    for lbl, mid in girder_entries:
        # lbl will be e.g., "G1", mid will be e.g., "G1M1"
        # Access girder specific keys dynamically:
        # val = input_dict.get(f"{KEY_MP_GIRDER_DEPTH}.{lbl}.{mid}")
        pass

    Returns:
        List[Tuple[str, str]]
    """
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0))

    entries = []

    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def _fig_or_placeholder(path, caption, width=S.FIGURE['default_width']):
    """Embed figure if path is provided (file already copied to assets), else show placeholder box.
    path is the relative path as pdflatex will see it (e.g. 'assets/plan.png').
    """
    if path:
        p = path.replace('\\', '/')
        return (r'\begin{figure}[H]' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[width=' + width + ']{' + p + '}\n'
                r'\caption*{' + caption + '}\n'
                r'\end{figure}')
    return (r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\fbox{\parbox{' + S.FIGURE['placeholder_width'] + '}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}' + '\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}')

def _fig_embed(path, caption, width=S.FIGURE['full_width'], height=None):
    """Embed a real figure when path is provided (already copied); otherwise use an fbox placeholder."""
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        return (r'\begin{figure}[H]' + '\n'
                r'\vspace{-\osdagFigureSkip}' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[' + opts + ']{' + p + '}\n'
                r'\vspace{\osdagFigureSkip}' + '\n'
                r'\caption*{\osdagCaptionFont ' + caption + '}\n'
                r'\vspace{-\osdagFigureSkip}' + '\n'
                r'\end{figure}')
    # fbox placeholder — ends the paragraph so consecutive placeholders stack
    # vertically instead of being set side by side on one over-wide line.
    return (r'\noindent\fbox{\parbox{' + S.FIGURE['placeholder_width'] + '}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}\par')


# ═══════════════════════════════════════════════════════════════════════════
# Multi-page tables (R1): longtable with a header that repeats on every page
# ═══════════════════════════════════════════════════════════════════════════

def count_columns(colspec):
    """Number of columns in a LaTeX array preamble such as
    ``|C{2.5cm}|>{\\centering\\arraybackslash}p{4.2cm}|l|``.

    Column letters are counted at brace depth 0; the braced arguments of
    ``p{}``/``L{}``-style columns and of ``>{}``, ``<{}``, ``@{}``, ``!{}``
    are skipped.
    """
    n, depth, i = 0, 0, 0
    while i < len(colspec):
        ch = colspec[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        elif depth == 0 and ch in 'lcrpmbXLCR':
            n += 1
        i += 1
    if n == 0:
        raise ValueError(f"no columns found in colspec {colspec!r}")
    return n


_CM_WIDTH = re.compile(r"([LCRpmb])\{([0-9]*\.?[0-9]+)cm\}")


def fit_colspec(colspec, available_cm=None):
    """Scale the absolute ``cm`` column widths of ``colspec`` so that the table
    (columns + 2 x ``\\tabcolsep`` per column + vertical rules) fits within the
    text width from ``styles.PAGE_GEOMETRY`` (R2: tables stay inside the
    printable area). Proportions are kept; a spec that already fits is
    returned unchanged. The default ``\\tabcolsep`` is assumed, which is the
    widest padding used, so locally tighter tables end up fitting as well.
    """
    widths = [float(m.group(2)) for m in _CM_WIDTH.finditer(colspec)]
    if not widths:
        return colspec
    ncols = count_columns(colspec)
    padding = (ncols * 2 * S._to_cm(S.TABLE["tabcolsep"])
               + (ncols + 1) * S._to_cm(S.TABLE["rule_width"]))
    available = (available_cm if available_cm is not None else S.text_width_cm()) - padding
    total = sum(widths)
    if total <= available:
        return colspec
    factor = available / total
    return _CM_WIDTH.sub(
        lambda m: f"{m.group(1)}{{{int(float(m.group(2)) * factor * 100) / 100:.2f}cm}}",
        colspec)


def _shade_header(header):
    """Prefix each header row with the header background colour."""
    rows = header.strip()
    return r'\rowcolor{osdagTableHeader}' + rows


# A table row terminator: "\\" or "\\[len]" that ends a row (followed by a
# \cline or \hline on the next line). Line breaks inside \makecell{..}
# are never followed by a rule, so they are not matched.
_ROW_END = re.compile(r"\\\\(\*)?(\[[^\]\n]*\])?(?=[ \t]*\r?\n[ \t]*\\(?:cline|hline))")
_MULTIROW = re.compile(r"\\multirow\{(\d+)\}")


def keep_row_groups_together(tex):
    """Forbid page breaks inside every ``\\multirow{n}`` row group (R2).

    A ``\\multirow{n}`` label is centred over its n rows; if ``longtable``
    breaks the page inside the group, the label is still drawn over all n
    rows and lands in the footer (the "G4" overlap). Ending the first n-1
    rows of each group with ``\\\\*`` (no page break after this row) moves the
    whole group to the next page instead. Rows after the group are untouched.
    """
    inserts = []
    for m in _MULTIROW.finditer(tex):
        n = int(m.group(1))
        if n < 2:
            continue
        pos = m.end()
        for _ in range(n - 1):
            end = _ROW_END.search(tex, pos)
            if end is None:
                break
            if not end.group(1):                  # not already "\\*"
                inserts.append(end.start() + 2)   # right after the two backslashes
            pos = end.end()
    if not inserts:
        return tex
    out, last = [], 0
    for at in sorted(set(inserts)):
        out.append(tex[last:at])
        out.append("*")
        last = at
    out.append(tex[last:])
    return "".join(out)


def _braced(tex, open_at):
    """(content, index after the closing brace) of the group starting at tex[open_at] == '{'."""
    depth = 0
    for i in range(open_at, len(tex)):
        if tex[i] == "{" and (i == 0 or tex[i - 1] != "\\"):
            depth += 1
        elif tex[i] == "}" and tex[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return tex[open_at + 1:i], i + 1
    raise ValueError("unbalanced braces")


_LT_BEGIN = re.compile(r"\\begin\{longtable\}(?=\{)")
_BODY_MARKERS = (r"\endlastfoot", r"\endfoot", r"\endhead")


def keep_table_starts_together(tex):
    """Start each longtable only where its head and first row unit fit (R2).

    longtable decides whether to start on the current page by measuring the
    head plus one strut-high line of the first row. When the first unbreakable
    unit (a tall row, or a ``\\multirow`` group bound by ``\\\\*``) is taller,
    TeX breaks *inside* the started table, before its first row: the old page
    gets an orphan "Continued on next page" foot and the new page shows the
    repeated head above the first head.

    For every longtable with an ``\\endfirsthead`` this inserts, just before
    ``\\begin{longtable}``, a probe that typesets the table's own first head
    and first row unit in a ``tabular`` with the same column spec (inside an
    unused box), followed by the *hard* ``\\Needspace*`` of that measured
    height plus a caption allowance: if it does not fit, the page is broken
    immediately, before longtable starts. (The soft ``\\needspace`` is not
    used: its cheap breakpoint is taken only once longtable's output routine
    is active, which is what produced the doubled head.) Nothing of the probe
    is printed.
    """
    out, last = [], 0
    for m in _LT_BEGIN.finditer(tex):
        spec, after_spec = _braced(tex, m.end())
        end = tex.find(r"\end{longtable}", after_spec)
        if end < 0:
            continue
        block = tex[after_spec:end]
        if r"\endfirsthead" not in block:
            continue
        head = "\n".join(line for line in block.split(r"\endfirsthead")[0].split("\n")
                         if not line.lstrip().startswith(r"\caption"))
        body_at = max(block.rfind(mk) + len(mk) for mk in _BODY_MARKERS if mk in block)
        body = block[body_at:]
        first_end = next((e for e in _ROW_END.finditer(body) if not e.group(1)), None)
        if first_end is None:
            continue
        rule_line_end = body.find("\n", first_end.end() + 1)
        first_unit = body[:rule_line_end if rule_line_end > 0 else len(body)]
        # \hbox (not \vbox): no paragraph/indent, so the probe itself never overflows
        probe = ("\\setbox\\osdagProbeBox\\hbox{\\let\\markSD\\relax"
                 "\\begin{tabular}{" + spec + "}" + head + "\n" + first_unit
                 + "\n\\end{tabular}}%\n"
                 "\\Needspace*{\\dimexpr\\ht\\osdagProbeBox+\\dp\\osdagProbeBox"
                 "+\\osdagCaptionAllowance\\relax}%\n")
        out.append(tex[last:m.start()])
        out.append(probe)
        last = m.start()
    out.append(tex[last:])
    return "".join(out)


def longtable_begin(colspec, header, caption=None, label=None, shade=True):
    """Opening of a ``longtable`` whose column header repeats on every page.

    Returns everything from ``\\begin{longtable}`` up to and including
    ``\\endlastfoot``; the caller appends the body rows and
    ``\\end{longtable}`` exactly as before.

    * first page  : caption + header                  (``\\endfirsthead``)
    * later pages : "caption (continued)" + header    (``\\endhead``)
    * page bottom : "Continued on next page" note     (``\\endfoot``)
    * last page   : nothing extra                     (``\\endlastfoot``)

    ``header`` is the header row(s) including the row terminator(s),
    e.g. ``r"\\textbf{A} & \\textbf{B} \\\\[\\osdagRowPad]"``.
    """
    colspec = fit_colspec(colspec)
    ncols = count_columns(colspec)
    head = _shade_header(header) if shade else header.strip()
    head_block = '\\hline\n' + head + '\n\\hline\n'

    first = ''
    cont = ''
    if caption:
        lbl = ('\\label{' + label + '}') if label else ''
        first = '\\caption{' + caption + '}' + lbl + '\\\\\n'
        cont = '\\caption[]{' + caption + ' ' + S.TABLE_CONTINUED_SUFFIX + '}\\\\\n'

    note = ('\\multicolumn{' + str(ncols) + '}{r}{\\osdagFootnoteFont '
            + S.TABLE_CONTINUES_NOTE + '}\\\\\n')

    return ('\\begin{longtable}{' + colspec + '}\n'
            + first + head_block + '\\endfirsthead\n'
            + cont + head_block + '\\endhead\n'
            + note + '\\endfoot\n'
            + '\\endlastfoot\n')


