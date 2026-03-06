import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

API_TOKEN = os.getenv("API_TOKEN", "")

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not API_TOKEN:
            return await call_next(request)

        path = request.url.path

        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Allow static files and docs
        if path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth == f"Bearer {API_TOKEN}":
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API token"},
        )
