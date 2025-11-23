from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
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
    background_tasks: BackgroundTasks,
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
        retry_count=0,
        max_retries=body.max_retries,
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

    # 使用 BackgroundTasks 執行背景 job
    background_tasks.add_task(run_pg_rebuild_job, job_id)

    return {"job_id": job_id}


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    # SQLAlchemy 2.0 style
    stmt = select(OpsJob).where(OpsJob.job_id == job_id)
    job = db.scalar(stmt)

    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    # Query steps
    steps_stmt = (
        select(OpsJobStep)
        .where(OpsJobStep.job_id == job_id)
        .order_by(OpsJobStep.step_order)
    )
    steps = list(db.scalars(steps_stmt).all())

    return JobOut(
        job_id=job.job_id,
        type=job.type,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        params=job.params,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
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


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """手動重試失敗的 Job"""
    # SQLAlchemy 2.0 style
    stmt = select(OpsJob).where(OpsJob.job_id == job_id)
    job = db.scalar(stmt)

    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    if job.status not in ["failed", "pending"]:
        raise HTTPException(
            status_code=400,
            detail=f"cannot retry job with status '{job.status}'"
        )

    if job.retry_count >= job.max_retries:
        raise HTTPException(
            status_code=400,
            detail=f"max retries ({job.max_retries}) exceeded"
        )

    # 增加重試次數並重新執行
    job.retry_count += 1
    job.status = "pending"
    job.finished_at = None
    db.commit()

    # 重新提交背景任務
    background_tasks.add_task(run_pg_rebuild_job, job_id)

    return {
        "message": "job retry scheduled",
        "job_id": job_id,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
    }
