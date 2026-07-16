import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


Role = Literal["admin", "underwriter", "dealer", "auditor"]

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-change-me-at-least-32-characters")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
	username: str
	role: Role


class LoginRequest(BaseModel):
	username: str = Field(min_length=1)
	password: str = Field(min_length=1)


class TokenResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"
	expires_in: int
	user: AuthenticatedUser


DEMO_USERS: dict[str, dict[str, str]] = {
	"admin": {"password": os.getenv("AUTH_ADMIN_PASSWORD", "admin-password"), "role": "admin"},
	"underwriter": {"password": os.getenv("AUTH_UNDERWRITER_PASSWORD", "underwriter-password"), "role": "underwriter"},
	"dealer": {"password": os.getenv("AUTH_DEALER_PASSWORD", "dealer-password"), "role": "dealer"},
	"auditor": {"password": os.getenv("AUTH_AUDITOR_PASSWORD", "auditor-password"), "role": "auditor"},
}


def authenticate_user(username: str, password: str) -> AuthenticatedUser | None:
	record = DEMO_USERS.get(username)
	if record is None or not secrets.compare_digest(password, record["password"]):
		return None
	return AuthenticatedUser(username=username, role=record["role"])  # type: ignore[arg-type]


def create_token_response(user: AuthenticatedUser) -> TokenResponse:
	expires_delta = timedelta(minutes=JWT_EXPIRE_MINUTES)
	expires_at = datetime.now(UTC) + expires_delta
	token = jwt.encode(
		{"sub": user.username, "role": user.role, "exp": expires_at},
		JWT_SECRET_KEY,
		algorithm=JWT_ALGORITHM,
	)
	return TokenResponse(access_token=token, expires_in=int(expires_delta.total_seconds()), user=user)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme)) -> AuthenticatedUser:
	if credentials is None:
		raise_authentication_error("missing_token", "Bearer token is required.")

	try:
		payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
	except jwt.ExpiredSignatureError:
		raise_authentication_error("token_expired", "Bearer token has expired.")
	except jwt.InvalidTokenError:
		raise_authentication_error("invalid_token", "Bearer token is invalid.")

	username = payload.get("sub")
	role = payload.get("role")
	if not isinstance(username, str) or role not in {"admin", "underwriter", "dealer", "auditor"}:
		raise_authentication_error("invalid_token_claims", "Bearer token claims are invalid.")

	return AuthenticatedUser(username=username, role=role)


def require_roles(*allowed_roles: Role):
	allowed = set(allowed_roles)

	def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
		if user.role not in allowed:
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN,
				detail={"code": "insufficient_role", "message": "User role is not allowed to perform this action."},
			)
		return user

	return dependency


def raise_authentication_error(code: str, message: str) -> None:
	raise HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail={"code": code, "message": message},
		headers={"WWW-Authenticate": "Bearer"},
	)