import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_MODELS_PATH = Path(__file__).resolve().parents[3] / "models.yaml"


@dataclass(frozen=True)
class ModelDefinition:
    id: str
    name: str
    description: str
    usage_limit: Optional[int]


@dataclass(frozen=True)
class ModelsConfig:
    default_model: str
    models: tuple[ModelDefinition, ...]

    def get(self, model_id: str) -> Optional[ModelDefinition]:
        return next((model for model in self.models if model.id == model_id), None)


class ModelsConfigError(Exception):
    pass


_cached_config: Optional[ModelsConfig] = None
_cached_mtime: Optional[float] = None


def models_config_path() -> Path:
    return Path(os.getenv("MODELS_CONFIG_PATH", str(DEFAULT_MODELS_PATH))).resolve()


def load_models_config() -> ModelsConfig:
    global _cached_config, _cached_mtime

    path = models_config_path()
    mtime = path.stat().st_mtime if path.exists() else None
    if _cached_config is not None and _cached_mtime == mtime:
        return _cached_config

    if not path.exists():
        raise ModelsConfigError(f"Models config not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    config = _parse_models_config(raw)
    _cached_config = config
    _cached_mtime = mtime
    return config


def _parse_models_config(raw: dict[str, Any]) -> ModelsConfig:
    items = raw.get("models")
    if not isinstance(items, list) or not items:
        raise ModelsConfigError("models.yaml must contain a non-empty 'models' list")

    models: list[ModelDefinition] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ModelsConfigError("Each model entry must be an object")

        model_id = str(item.get("id") or "").strip()
        if not model_id:
            raise ModelsConfigError("Each model entry must contain a non-empty 'id'")
        if model_id in seen:
            raise ModelsConfigError(f"Duplicate model id in models.yaml: {model_id}")
        seen.add(model_id)

        raw_limit = item.get("usage_limit")
        if raw_limit in (None, ""):
            usage_limit = None
        else:
            usage_limit = int(raw_limit)
            if usage_limit < 0:
                raise ModelsConfigError(f"usage_limit must be non-negative for model: {model_id}")

        models.append(
            ModelDefinition(
                id=model_id,
                name=str(item.get("name") or model_id),
                description=str(item.get("description") or ""),
                usage_limit=usage_limit,
            )
        )

    default_model = str(raw.get("default_model") or models[0].id).strip()
    if default_model not in seen:
        raise ModelsConfigError("default_model must reference a model from the models list")

    return ModelsConfig(default_model=default_model, models=tuple(models))


def default_model_id() -> str:
    return load_models_config().default_model
