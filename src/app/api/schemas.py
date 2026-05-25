from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from ..services.model_config import default_model_id


DEFAULT_LLM_MODEL = default_model_id()


class ConvertResponse(BaseModel):
    success: bool
    latex_content: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None


class CompareRequest(BaseModel):
    template_content: str = Field(..., min_length=10, description="Template text")
    document_content: str = Field(..., min_length=10, description="Document text")
    model: str = Field(default=DEFAULT_LLM_MODEL, description="LLM model")
    parallel: bool = Field(default=True, description="Run checks in parallel")


class ErrorItem(BaseModel):
    section: str
    error_type: Literal["structural", "content", "formatting", "typography"]
    description: str
    severity: Literal["critical", "high", "medium", "low"]


class CompareResponse(BaseModel):
    errors: List[ErrorItem]
    compliance_score: int
    summary: str


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="ITPort login or email")
    password: str = Field(..., min_length=1, description="ITPort password")


class UserResponse(BaseModel):
    email: str
    redirect: Optional[str] = None
    role: Literal["admin", "user"] = "user"
    last_login_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse


class ModelResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    usage_limit: Optional[int] = None
    used_count: int = 0
    remaining: Optional[int] = None


class ModelsResponse(BaseModel):
    default_model: str
    models: List[ModelResponse]


class TemplateResponse(BaseModel):
    id: str
    name: str
    size: int


class TemplatesResponse(BaseModel):
    templates: List[TemplateResponse]


class UsageResetRequest(BaseModel):
    user_email: Optional[str] = Field(default=None, description="Reset usage for this user only")
    model: Optional[str] = Field(default=None, description="Reset usage for this model only")


class UsageResetResponse(BaseModel):
    reset_records: int
