import sys
import os
import logging
import traceback
from pathlib import Path

# Добавляем src в путь, чтобы импорты работали
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from converter_pkg.main import convert_to_latex

logger = logging.getLogger(__name__)

class ConverterService:
    @staticmethod
    def convert_docx_to_latex(
        docx_path: str,
        output_path: str,
        image_dir: str = "uploads/images"
    ) -> dict:
        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            os.makedirs(image_dir, exist_ok=True)
            
            convert_to_latex(docx_path, output_path, image_dir)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                latex_content = f.read()
            
            return {
                "success": True,
                "latex_content": latex_content,
                "file_path": output_path,
                "error": None
            }
        except Exception as e:
            logger.exception("DOCX to LaTeX conversion failed for %s", docx_path)
            return {
                "success": False,
                "latex_content": None,
                "file_path": None,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
