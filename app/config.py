import os
from pydantic import BaseSettings


def load_from_file_or_env(path: str, env_name: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    v = os.environ.get(env_name)
    if not v:
        raise RuntimeError(f"No secret found at {path} or env {env_name}")
    return v


class Settings(BaseSettings):
    ENV: str = os.environ.get("ENV", "prod")

    # 這兩個通常會由 Vault Agent 注入檔案
    API_KEY_PATH: str = "/vault/secrets/api-key"
    DB_URL_PATH: str = "/vault/secrets/db-url"

    OPS_API_KEY_ENV: str = "OPS_API_KEY"
    OPS_DB_URL_ENV: str = "OPS_DB_URL"

    @property
    def API_KEY(self) -> str:
        return load_from_file_or_env(self.API_KEY_PATH, self.OPS_API_KEY_ENV)

    @property
    def DATABASE_URL(self) -> str:
        return load_from_file_or_env(self.DB_URL_PATH, self.OPS_DB_URL_ENV)

    # 允許操作的 namespace
    ALLOWED_NAMESPACES: set[str] = {"prod", "staging"}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
