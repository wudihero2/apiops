import asyncio
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import verify_api_key, get_actor, get_source_ip
from ..config import settings
from ..db import get_db
from ..jobs.pg_rebuild import gen_job_id, run_pg_rebuild_job, now_utc
from ..models import OpsJob, OpsJobStep
from ..schemas import JobOut, JobStepOut, PgRebuildRequest

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/jobs/pg-rebuild")
async def create_pg_rebuild_job(
    body: PgRebuildRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    if body.namespace not in settings.ALLOWED_NAMESPACES:
        raise HTTPException(status_code=403, detail="namespace not allowed")

    job_id = gen_job_id("pg-rebuild")

    job = OpsJob(
        job_id=job_id,
        type="pg-rebuild",
        status="pending",
        created_at=now_utc(),
        finished_at=None,
        params=body.dict(),
        actor=get_actor(request),
        source_ip=get_source_ip(request),
    )
    db.add(job)
    db.commit()

    steps_def = [
        ("scale_sts_to_zero", 1),
        ("wait_pods_down", 2),
        ("delete_pvc", 3),
        ("scale_sts_to_target", 4),
        ("wait_pods_ready", 5),
    ]
    for name, order in steps_def:
        s = OpsJobStep(
            job_id=job_id,
            name=name,
            step_order=order,
            status="pending",
        )
        db.add(s)
    db.commit()

    # 背景執行 job
    asyncio.create_task(run_pg_rebuild_job(job_id))

    return {"job_id": job_id}


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job: OpsJob | None = db.query(OpsJob).filter_by(job_id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    steps: List[OpsJobStep] = (
        db.query(OpsJobStep)
        .filter_by(job_id=job_id)
        .order_by(OpsJobStep.step_order)
        .all()
    )

    return JobOut(
        job_id=job.job_id,
        type=job.type,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        params=job.params,
        steps=[
            JobStepOut(
                name=s.name,
                order=s.step_order,
                status=s.status,
                detail=s.detail,
                started_at=s.started_at,
                finished_at=s.finished_at,
            )
            for s in steps
        ],
    )
