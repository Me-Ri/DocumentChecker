from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


_ALIGNMENT_XML_MAP = {
    'start': WD_ALIGN_PARAGRAPH.LEFT,
    'end': WD_ALIGN_PARAGRAPH.RIGHT,
    'left': WD_ALIGN_PARAGRAPH.LEFT,
    'center': WD_ALIGN_PARAGRAPH.CENTER,
    'right': WD_ALIGN_PARAGRAPH.RIGHT,
    'both': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'distribute': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'mediumKashida': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'highKashida': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'lowKashida': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'thaiDistribute': WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def latex_special_chars(text):
    if text is None:
        return ""

    replace_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '>': r'$>$',
        '<': r'$<$'
    }

    for char, new_char in replace_chars.items():
        text = text.replace(char, new_char)

    return text


def get_paragraph_alignment(paragraph):
    try:
        return paragraph.alignment
    except (ValueError, AttributeError):
        p_pr = getattr(paragraph._p, 'pPr', None)
        jc = getattr(p_pr, 'jc', None) if p_pr is not None else None
        if jc is None:
            return None

        return _ALIGNMENT_XML_MAP.get(jc.get(qn('w:val')))


def get_column_alignment(table, col_index):
    for row in table.rows:
        if col_index >= len(row.cells):
            continue
        cell = row.cells[col_index]
        if cell.paragraphs:
            para = cell.paragraphs[0]
            alignment = get_paragraph_alignment(para)
            if alignment is not None:
                if alignment == WD_ALIGN_PARAGRAPH.CENTER:
                    return 'c'
                elif alignment == WD_ALIGN_PARAGRAPH.RIGHT:
                    return 'r'
                else:
                    return 'l'
    return 'l'
