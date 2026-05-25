import sys
import logging
from pathlib import Path

# Добавляем src в путь
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from llm_pkg.comparator import compare_documents
from app.api.schemas import DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)

class ComparatorService:
    @staticmethod
    def compare(
        template_content: str,
        document_content: str,
        model: str = DEFAULT_LLM_MODEL,
        parallel: bool = True
    ) -> dict:
        try:
            result = compare_documents(
                template_content=template_content,
                document_content=document_content,
                model=model,
                parallel=parallel
            )
            return {"success": True, "data": result, "error": None}
        except Exception as e:
            logger.exception("Document comparison service failed")
            return {"success": False, "data": None, "error": str(e)}
