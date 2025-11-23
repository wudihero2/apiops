from fastapi import Header, HTTPException, Request

from .config import settings


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


def get_actor(request: Request) -> str:
    # 之後可以改接 SSO，例如 X-User-Email
    return request.headers.get("X-Actor") or request.headers.get("X-User-Email") or "unknown"


def get_source_ip(request: Request) -> str | None:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None
