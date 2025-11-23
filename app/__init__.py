from fastapi import FastAPI

from .config import settings
from .db import init_db
from .routes import health, ops_primitive, jobs


def create_app() -> FastAPI:
    app = FastAPI(
        title="ApiOps",
        version="0.1.0",
    )

    # 初始化 DB (只做 metadata.create_all; 正式可以改 Alembic)
    init_db()

    # router
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(ops_primitive.router, prefix="/ops", tags=["ops"])
    app.include_router(jobs.router, prefix="/ops", tags=["jobs"])

    @app.get("/")
    def root():
        return {"name": "apiops", "version": "0.1.0", "env": settings.ENV}

    return app
