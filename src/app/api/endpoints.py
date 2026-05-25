import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from .schemas import (
    DEFAULT_LLM_MODEL,
    CompareRequest,
    CompareResponse,
    ConvertResponse,
    ErrorItem,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    ModelResponse,
    ModelsResponse,
    TemplateResponse,
    TemplatesResponse,
    UsageResetRequest,
    UsageResetResponse,
    UserResponse,
)
from ..database import ModelUsageRepository, UserRecord
from ..services.auth import (
    AuthService,
    ExternalAuthError,
    InvalidCredentialsError,
    get_current_admin,
    get_current_token,
    get_current_user,
    user_role,
)
from ..services.comparator import ComparatorService
from ..services.converter import ConverterService
from ..services.model_config import ModelDefinition, ModelsConfigError, default_model_id, load_models_config
from ..services.templates import TemplateService

router = APIRouter()
logger = logging.getLogger(__name__)


def _upload_meta(file: UploadFile) -> dict:
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": getattr(file, "size", None),
    }


def _error_items(data: dict) -> list[ErrorItem]:
    return [
        ErrorItem(
            section=err.get("section", "Общий документ"),
            error_type=err.get("error_type", "structural"),
            description=err.get("description", ""),
            severity=err.get("severity", "low"),
        )
        for err in data.get("errors", [])
    ]


def _user_response(user: UserRecord) -> UserResponse:
    return UserResponse(
        email=user.email,
        redirect=user.redirect,
        role=user_role(user),
        last_login_at=user.last_login_at,
    )


def _model_response(model: ModelDefinition, user: UserRecord) -> ModelResponse:
    used_count = ModelUsageRepository().get_usage(user.email, model.id)
    remaining = None if model.usage_limit is None else max(model.usage_limit - used_count, 0)
    return ModelResponse(
        id=model.id,
        name=model.name,
        description=model.description,
        usage_limit=model.usage_limit,
        used_count=used_count,
        remaining=remaining,
    )


def _get_model_or_400(model_id: str) -> ModelDefinition:
    try:
        config = load_models_config()
    except ModelsConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    model = config.get(model_id)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_id}")
    return model


def _consume_model_usage(user: UserRecord, model: ModelDefinition) -> None:
    used_count = ModelUsageRepository().consume_usage(user.email, model.id, model.usage_limit)
    if used_count is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Usage limit exceeded for model: {model.id}",
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@router.post("/api/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    try:
        result = AuthService().login(username=req.username, password=req.password)
        return LoginResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_at=result.expires_at,
            user=_user_response(result.user),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ExternalAuthError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/api/auth/me", response_model=UserResponse)
async def auth_me(current_user: UserRecord = Depends(get_current_user)):
    return _user_response(current_user)


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: UserRecord = Depends(get_current_user),
    token: str = Depends(get_current_token),
):
    AuthService().logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/models", response_model=ModelsResponse)
async def list_models(current_user: UserRecord = Depends(get_current_user)):
    try:
        config = load_models_config()
    except ModelsConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ModelsResponse(
        default_model=config.default_model,
        models=[_model_response(model, current_user) for model in config.models],
    )


@router.get("/api/templates", response_model=TemplatesResponse)
async def list_templates(current_user: UserRecord = Depends(get_current_user)):
    templates = TemplateService().list_templates()
    return TemplatesResponse(
        templates=[
            TemplateResponse(id=template.id, name=template.name, size=template.size)
            for template in templates
        ]
    )


@router.post("/api/admin/templates", response_model=TemplateResponse)
async def upload_template(
    template_file: UploadFile = File(...),
    current_admin: UserRecord = Depends(get_current_admin),
):
    try:
        template = TemplateService().save_template(template_file.filename, template_file.file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.exception("Template upload failed")
        raise HTTPException(status_code=500, detail="Failed to save template") from exc

    return TemplateResponse(id=template.id, name=template.name, size=template.size)


@router.post("/api/admin/usage/reset", response_model=UsageResetResponse)
async def reset_usage(
    req: UsageResetRequest,
    current_admin: UserRecord = Depends(get_current_admin),
):
    if req.model:
        _get_model_or_400(req.model)
    reset_records = ModelUsageRepository().reset_usage(
        user_email=req.user_email,
        model_id=req.model,
    )
    return UsageResetResponse(reset_records=reset_records)


@router.post("/api/convert", response_model=ConvertResponse)
async def convert_docx(
    docx_file: UploadFile = File(...),
    current_user: UserRecord = Depends(get_current_user),
):
    if not docx_file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Только .docx файлы")

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / docx_file.filename
        output_path = Path(tmpdir) / docx_file.filename.replace(".docx", ".tex")
        image_dir = Path(tmpdir) / "images"
        image_dir.mkdir(exist_ok=True)

        with docx_path.open("wb") as buffer:
            shutil.copyfileobj(docx_file.file, buffer)

        result = ConverterService.convert_docx_to_latex(
            docx_path=str(docx_path),
            output_path=str(output_path),
            image_dir=str(image_dir),
        )
        return ConvertResponse(**result)


@router.post("/api/compare", response_model=CompareResponse)
async def compare_documents(
    req: CompareRequest,
    current_user: UserRecord = Depends(get_current_user),
):
    try:
        model = _get_model_or_400(req.model)
        _consume_model_usage(current_user, model)
        result = ComparatorService.compare(
            template_content=req.template_content,
            document_content=req.document_content,
            model=model.id,
            parallel=req.parallel,
        )

        if not result["success"]:
            logger.error("Document comparison failed: %s", result["error"])
            raise HTTPException(status_code=500, detail=result["error"])

        data = result["data"]
        errors = _error_items(data)

        return CompareResponse(
            errors=errors,
            compliance_score=data.get("compliance_score", 0),
            summary=data.get("summary", ""),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected /api/compare failure")
        raise


@router.post("/api/validate-upload", response_model=CompareResponse)
async def validate_and_compare(
    template_file: UploadFile | None = File(None),
    document_file: UploadFile = File(...),
    model: str = Form(DEFAULT_LLM_MODEL),
    template_name: str | None = Form(None),
    current_user: UserRecord = Depends(get_current_user),
):
    selected_model = _get_model_or_400(model or default_model_id())
    _consume_model_usage(current_user, selected_model)

    logger.info(
        "validate-upload started: template=%s template_name=%s document=%s model=%s",
        _upload_meta(template_file) if template_file else None,
        template_name,
        _upload_meta(document_file),
        selected_model.id,
    )

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_dir = tmpdir / "images"
            image_dir.mkdir(exist_ok=True)

            logger.info("validate-upload saving uploaded files")
            doc_path = tmpdir / f"doc_{document_file.filename}"

            if template_name:
                try:
                    tpl_path = TemplateService().resolve_template_path(template_name)
                except FileNotFoundError as exc:
                    raise HTTPException(status_code=404, detail="Template not found") from exc
            elif template_file is not None:
                tpl_path = tmpdir / f"tpl_{template_file.filename}"
                with tpl_path.open("wb") as f:
                    shutil.copyfileobj(template_file.file, f)
            else:
                raise HTTPException(status_code=400, detail="Template file or template_name is required")

            with doc_path.open("wb") as f:
                shutil.copyfileobj(document_file.file, f)

            tpl_tex = tmpdir / "template.tex"
            doc_tex = tmpdir / "document.tex"

            logger.info("validate-upload converting template")
            tpl_res = ConverterService.convert_docx_to_latex(str(tpl_path), str(tpl_tex), str(image_dir))
            if not tpl_res["success"]:
                logger.error("Template conversion failed: %s", tpl_res["error"])
                raise HTTPException(status_code=500, detail=f"Шаблон: {tpl_res['error']}")

            logger.info("validate-upload converting document")
            doc_res = ConverterService.convert_docx_to_latex(str(doc_path), str(doc_tex), str(image_dir))
            if not doc_res["success"]:
                logger.error("Document conversion failed: %s", doc_res["error"])
                raise HTTPException(status_code=500, detail=f"Документ: {doc_res['error']}")

            logger.info("validate-upload comparing documents")
            result = ComparatorService.compare(
                template_content=tpl_res["latex_content"],
                document_content=doc_res["latex_content"],
                model=selected_model.id,
            )

            if not result["success"]:
                logger.error("Document comparison failed: %s", result["error"])
                raise HTTPException(status_code=500, detail=result["error"])

            data = result["data"]
            errors = _error_items(data)

            logger.info(
                "validate-upload finished: errors=%s compliance_score=%s",
                len(errors),
                data.get("compliance_score", 0),
            )
            return CompareResponse(
                errors=errors,
                compliance_score=data.get("compliance_score", 0),
                summary=data.get("summary", ""),
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected /api/validate-upload failure")
        raise
