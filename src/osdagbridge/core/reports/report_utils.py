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
    # fbox placeholder — matches template exactly
    return (r'\noindent\fbox{\parbox{' + S.FIGURE['placeholder_width'] + '}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}')


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


def _shade_header(header):
    """Prefix each header row with the header background colour."""
    rows = header.strip()
    return r'\rowcolor{osdagTableHeader}' + rows


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


