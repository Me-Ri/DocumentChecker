import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from lxml import html

from ..database import SessionRepository, UserRecord, UserRepository


ITPORT_BASE_URL = "https://itport.ugrasu.ru"
AUTH_TIMEOUT_SECONDS = 30
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "12"))

security = HTTPBearer(auto_error=False)


class ExternalAuthError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def _configured_admin_logins() -> set[str]:
    raw = os.getenv("ADMIN_LOGINS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def is_admin_login(login: str) -> bool:
    return login.strip().lower() in _configured_admin_logins()


def user_role(user: UserRecord) -> str:
    return "admin" if is_admin_login(user.email) else "user"


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserRecord


class ItportAuthClient:
    def login(self, username: str, password: str) -> dict:
        try:
            with requests.Session() as session:
                csrf_token = self._fetch_csrf_token(session)
                response = session.post(
                    f"{ITPORT_BASE_URL}/login",
                    headers={
                        "X-CSRF-TOKEN": csrf_token,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "email": username,
                        "password": password,
                        "form": 0,
                        "group": "",
                        "ffullname": "",
                        "bithday": "",
                        "passport": "",
                        "snils": "",
                        "inn": "",
                    },
                    timeout=AUTH_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
        except requests.RequestException as exc:
            raise ExternalAuthError("Сервис авторизации временно недоступен") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise ExternalAuthError("Сервис авторизации вернул некорректный JSON") from exc

        if data.get("type") == "danger":
            message = data.get("message") or data.get("text") or "Неверный логин или пароль"
            raise InvalidCredentialsError(message)

        if "redirect" not in data:
            raise ExternalAuthError("Сервис авторизации не вернул redirect")

        return data

    def _fetch_csrf_token(self, session: requests.Session) -> str:
        response = session.get(ITPORT_BASE_URL, timeout=AUTH_TIMEOUT_SECONDS)
        response.raise_for_status()

        document = html.fromstring(response.text)
        tokens = document.xpath("//head/meta[@name='csrf-token']/@content")
        if not tokens:
            raise ExternalAuthError("CSRF-токен не найден на странице авторизации")

        return tokens[0]


class AuthService:
    def __init__(
        self,
        auth_client: Optional[ItportAuthClient] = None,
        users: Optional[UserRepository] = None,
        sessions: Optional[SessionRepository] = None,
    ) -> None:
        self.auth_client = auth_client or ItportAuthClient()
        self.users = users or UserRepository()
        self.sessions = sessions or SessionRepository()

    def login(self, username: str, password: str) -> LoginResult:
        auth_payload = self.auth_client.login(username=username, password=password)
        user = self.users.upsert_after_login(
            email=username,
            redirect=auth_payload.get("redirect"),
            auth_payload=auth_payload,
        )

        token = secrets.token_urlsafe(32)
        session = self.sessions.create(
            token_hash=self._hash_token(token),
            user_email=user.email,
            ttl=timedelta(hours=SESSION_TTL_HOURS),
        )

        return LoginResult(
            access_token=token,
            token_type="bearer",
            expires_at=session.expires_at,
            user=user,
        )

    def authenticate(self, token: str) -> UserRecord:
        session = self.sessions.get_active(self._hash_token(token))
        if session is None:
            raise InvalidCredentialsError("Сессия не найдена или истекла")

        user = self.users.get_by_email(session.user_email)
        if user is None:
            raise InvalidCredentialsError("Пользователь не найден")

        return user

    def logout(self, token: str) -> None:
        self.sessions.revoke(self._hash_token(token))

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _extract_bearer_token(credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserRecord:
    token = _extract_bearer_token(credentials)
    try:
        return AuthService().authenticate(token)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_admin(
    current_user: UserRecord = Depends(get_current_user),
) -> UserRecord:
    if not is_admin_login(current_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator rights are required",
        )
    return current_user


async def get_current_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    return _extract_bearer_token(credentials)
