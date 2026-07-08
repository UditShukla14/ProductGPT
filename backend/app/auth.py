"""Bearer token authentication for public API endpoints."""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer_scheme = HTTPBearer()


def verify_public_api_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """Validate the Bearer token against PUBLIC_API_TOKEN.

    Returns the token on success so downstream code can log/audit if needed.
    Raises 401 if the token is missing/empty and 403 if it doesn't match.
    """
    if not settings.public_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Public API authentication is not configured on the server.",
        )

    if not secrets.compare_digest(credentials.credentials, settings.public_api_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API token.",
        )

    return credentials.credentials
