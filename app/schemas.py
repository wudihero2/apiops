from datetime import datetime

from pydantic import BaseModel


class ScaleRequest(BaseModel):
    replicas: int


class PgRebuildRequest(BaseModel):
    namespace: str
    statefulset: str
    ordinal: int
    target_replicas: int = 1
    max_retries: int = 3


class JobStepOut(BaseModel):
    name: str
    order: int
    status: str
    detail: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobOut(BaseModel):
    job_id: str
    type: str
    status: str
    created_at: datetime
    finished_at: datetime | None = None
    params: dict[str, any]
    retry_count: int
    max_retries: int
    steps: list[JobStepOut]
