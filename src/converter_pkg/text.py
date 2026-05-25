from docx.enum.text import WD_ALIGN_PARAGRAPH
from pylatex import NoEscape

from .utils import get_paragraph_alignment, latex_special_chars


def are_runs_similar(run1, run2):
    if run1.bold != run2.bold:
        return False
    if run1.italic != run2.italic:
        return False
    if run1.underline != run2.underline:
        return False
    if run1.font.name != run2.font.name:
        return False
    if run1.font.size != run2.font.size:
        return False
    return True


def merge_similar_runs(paragraph):
    if len(paragraph.runs) <= 1:
        return paragraph

    merged_text = []
    current_run = None

    for run in paragraph.runs:
        if current_run is None:
            current_run = run
            merged_text.append(run.text)
        elif are_runs_similar(current_run, run):
            merged_text[-1] += run.text
        else:
            current_run = run
            merged_text.append(run.text)

    return merged_text


def format_runs_in_paragraph(paragraph, escape_func):
    text = ''

    merged_runs = []
    current_text = ''
    current_run = None

    for run in paragraph.runs:
        if current_run is None:
            current_run = run
            current_text = run.text
        elif are_runs_similar(current_run, run):
            current_text += run.text
        else:
            merged_runs.append((current_text, current_run))
            current_run = run
            current_text = run.text

    if current_run is not None:
        merged_runs.append((current_text, current_run))

    for run_text, run in merged_runs:
        if not run_text.strip():
            run_text = escape_func(run_text)
        else:
            run_text = escape_func(run_text)
            if run.bold and run.italic:
                run_text = f'\\textbf{{\\textit{{{run_text}}}}}'
            elif run.bold:
                run_text = f'\\textbf{{{run_text}}}'
            elif run.italic:
                run_text = f'\\textit{{{run_text}}}'
            elif run.underline:
                run_text = f'\\underline{{{run_text}}}'

        font_name = run.font.name
        font_size = run.font.size
        if run.font.size is not None:
            font_size = font_size.pt

        line_spacing = paragraph.paragraph_format.line_spacing
        line_spacing_rule = paragraph.paragraph_format.line_spacing_rule

        if line_spacing is not None:
            if isinstance(line_spacing, (int, float)):
                if line_spacing_rule in [3, 4]:
                    line_spacing_pt = round(line_spacing / 12700, 2)
                else:
                    line_spacing_pt = line_spacing
            else:
                line_spacing_pt = str(line_spacing)
        else:
            line_spacing_pt = None

        run_text += f'% Шрифт-{font_name} Размер шрифта-{font_size} Межстрочный интервал-{line_spacing_pt} Правило-{line_spacing_rule} %\n'

        text += run_text

    return text


def parse_paragraphs(paragraphs, latex_doc, flag_itemize, flag_enumerate):

    if paragraphs.style.name.startswith("Heading"):
        if flag_itemize:
            latex_doc.append(NoEscape(r'\end{itemize}'))
            flag_itemize = False

        if flag_enumerate:
            latex_doc.append(NoEscape(r'\end{enumerate}'))
            flag_enumerate = False

        level = int(paragraphs.style.name.split()[1])
        if level == 1:
            latex_doc.append(NoEscape(f'\\section{{{latex_special_chars(paragraphs.text)}}}'))
        elif level == 2:
            latex_doc.append(NoEscape(f'\\subsection{{{latex_special_chars(paragraphs.text)}}}'))
        elif level == 3:
            latex_doc.append(NoEscape(f'\\subsubsection{{{latex_special_chars(paragraphs.text)}}}'))
        else:
            latex_doc.append(NoEscape(f'\\paragraph{{{latex_special_chars(paragraphs.text)}}}'))

        return flag_itemize, flag_enumerate

    text = format_runs_in_paragraph(paragraphs, latex_special_chars)

    alignment = get_paragraph_alignment(paragraphs)
    if alignment == WD_ALIGN_PARAGRAPH.LEFT:
        latex_alignment = "flushleft"
    elif alignment == WD_ALIGN_PARAGRAPH.CENTER:
        latex_alignment = 'center'
    elif alignment == WD_ALIGN_PARAGRAPH.RIGHT:
        latex_alignment = 'flushright'
    else:
        latex_alignment = 'flushleft'

    if text.strip():
        latex_doc.append(NoEscape(f'\\begin{{{latex_alignment}}}'))
        latex_doc.append(NoEscape(text))
        latex_doc.append(NoEscape(f'\\end{{{latex_alignment}}}'))

    return flag_itemize, flag_enumerate


def parse_list_paragraphs(paragraphs, latex_doc, flag_itemize, flag_enumerate):
    text = format_runs_in_paragraph(paragraphs, latex_special_chars)

    if paragraphs.style.name == 'List Bullet':
        if not flag_itemize:
            if flag_enumerate:
                latex_doc.append(NoEscape(r'\end{enumerate}'))
                flag_enumerate = False

            flag_itemize = True
            latex_doc.append(NoEscape(r'\begin{itemize}'))

        latex_doc.append(NoEscape(r'\item ' + text))
    elif paragraphs.style.name in ['List Number', 'List Paragraph']:
        if not flag_enumerate:
            if flag_itemize:
                latex_doc.append(NoEscape(r'\end{itemize}'))
                flag_itemize = False

            flag_enumerate = True
            latex_doc.append(NoEscape(r'\begin{enumerate}'))
        latex_doc.append(NoEscape(r'\item ' + text))

    return flag_itemize, flag_enumerate
