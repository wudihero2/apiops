from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ScaleRequest(BaseModel):
    replicas: int


class PgRebuildRequest(BaseModel):
    namespace: str
    statefulset: str
    ordinal: int
    target_replicas: int = 1


class JobStepOut(BaseModel):
    name: str
    order: int
    status: str
    detail: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class JobOut(BaseModel):
    job_id: str
    type: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    params: Dict[str, Any]
    steps: List[JobStepOut]
