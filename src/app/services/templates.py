import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "doctempletes"
ALLOWED_TEMPLATE_SUFFIXES = {".docx"}
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


@dataclass(frozen=True)
class TemplateDefinition:
    id: str
    name: str
    size: int


class TemplateService:
    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or Path(
            os.getenv("DOCTEMPLATES_DIR", str(DEFAULT_TEMPLATE_DIR))
        ).resolve()

    def list_templates(self) -> list[TemplateDefinition]:
        if not self.template_dir.exists():
            return []

        templates: list[TemplateDefinition] = []
        for path in sorted(self.template_dir.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file() or path.suffix.lower() not in ALLOWED_TEMPLATE_SUFFIXES:
                continue
            templates.append(
                TemplateDefinition(
                    id=path.name,
                    name=path.stem,
                    size=path.stat().st_size,
                )
            )
        return templates

    def save_template(self, filename: str | None, source: BinaryIO) -> TemplateDefinition:
        safe_name = self._safe_template_filename(filename)
        self.template_dir.mkdir(parents=True, exist_ok=True)

        destination = (self.template_dir / safe_name).resolve()
        if self.template_dir not in destination.parents:
            raise ValueError("Invalid template filename")

        with destination.open("wb") as file:
            shutil.copyfileobj(source, file)

        return TemplateDefinition(
            id=destination.name,
            name=destination.stem,
            size=destination.stat().st_size,
        )

    def resolve_template_path(self, template_id: str) -> Path:
        if not template_id or Path(template_id).name != template_id:
            raise FileNotFoundError("Invalid template id")

        path = (self.template_dir / template_id).resolve()
        if self.template_dir not in path.parents:
            raise FileNotFoundError("Invalid template id")
        if not path.is_file() or path.suffix.lower() not in ALLOWED_TEMPLATE_SUFFIXES:
            raise FileNotFoundError("Template not found")
        return path

    @staticmethod
    def _safe_template_filename(filename: str | None) -> str:
        raw_name = Path(filename or "").name.strip()
        if not raw_name:
            raise ValueError("Template filename is required")

        suffix = Path(raw_name).suffix.lower()
        if suffix not in ALLOWED_TEMPLATE_SUFFIXES:
            raise ValueError("Only .docx templates are allowed")

        stem = Path(raw_name).stem.strip().strip(".")
        stem = INVALID_FILENAME_CHARS.sub("_", stem).strip()
        if not stem:
            raise ValueError("Template filename is required")

        return f"{stem}{suffix}"
