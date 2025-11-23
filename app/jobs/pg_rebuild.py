import asyncio
from datetime import datetime, timezone
import uuid

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..k8s_client import core_v1, apps_v1
from ..models import OpsJob, OpsJobStep


def now_utc():
    return datetime.now(timezone.utc)


def gen_job_id(job_type: str) -> str:
    return f"{now_utc().isoformat()}_{job_type}_{uuid.uuid4().hex[:8]}"


def run_pg_rebuild_job(job_id: str):
    """
    同步包裝函數，用於 FastAPI BackgroundTasks。
    在新的 event loop 中執行 async job。
    """
    asyncio.run(_run_pg_rebuild_job_async(job_id))


async def _run_pg_rebuild_job_async(job_id: str):
    """
    背景執行 PG rebuild 流程：
    1. scale sts -> 0
    2. 等所有 pod down
    3. delete 對應 PVC
    4. scale sts -> target_replicas
    5. 等 pod ready

    支援自動重試：從失敗步驟繼續執行
    """
    # 使用 context manager 管理 session
    with SessionLocal() as db:
        try:
            # SQLAlchemy 2.0 style: select() + where()
            stmt = select(OpsJob).where(OpsJob.job_id == job_id)
            job = db.scalar(stmt)

            if not job:
                raise RuntimeError(f"job {job_id} not found")

            job.status = "running"
            db.commit()

            params = job.params
            ns = params["namespace"]
            sts_name = params["statefulset"]
            ordinal = params["ordinal"]
            target_replicas = params["target_replicas"]
            pvc_name = f"data-{sts_name}-{ordinal}"

            if ns not in settings.ALLOWED_NAMESPACES:
                raise RuntimeError(f"namespace {ns} not allowed")

            # 查詢已完成的步驟（用於重試時跳過）
            steps_stmt = (
                select(OpsJobStep)
                .where(OpsJobStep.job_id == job_id, OpsJobStep.status == "success")
            )
            completed_steps = {s.name for s in db.scalars(steps_stmt).all()}

            async def run_step(step_name: str, func):
                # SQLAlchemy 2.0 style
                step_stmt = select(OpsJobStep).where(
                    OpsJobStep.job_id == job_id,
                    OpsJobStep.name == step_name
                )
                step = db.scalar(step_stmt)

                if not step:
                    raise RuntimeError(f"step {step_name} not found")

                step.status = "running"
                step.started_at = now_utc()
                step.detail = None
                db.commit()

                try:
                    detail = await func()
                    step.status = "success"
                    step.detail = detail
                    step.finished_at = now_utc()
                    db.commit()
                except Exception as e:
                    step.status = "failed"
                    step.detail = f"error: {e}"
                    step.finished_at = now_utc()
                    job.status = "failed"
                    job.finished_at = now_utc()
                    db.commit()
                    raise

            async def step_scale_to_zero():
                patch = {"spec": {"replicas": 0}}
                apps_v1.patch_namespaced_stateful_set(
                    name=sts_name,
                    namespace=ns,
                    body=patch,
                )
                return "scaled to 0"

            async def step_wait_pods_down():
                # 這裡直接列出 namespace 所有 pod，再用 name prefix 過濾
                for _ in range(60):  # 最多等 5 分鐘
                    pods = core_v1.list_namespaced_pod(namespace=ns).items
                    related = [
                        p for p in pods
                        if p.metadata.name.startswith(f"{sts_name}-")
                    ]
                    if not related:
                        return "all pods down"

                    names = [p.metadata.name for p in related]
                    # 更新 detail
                    step_stmt = select(OpsJobStep).where(
                        OpsJobStep.job_id == job_id,
                        OpsJobStep.name == "wait_pods_down"
                    )
                    step = db.scalar(step_stmt)
                    if step:
                        step.detail = f"remaining pods: {names}"
                        db.commit()
                    await asyncio.sleep(5)
                raise RuntimeError("timeout waiting pods down")

            async def step_delete_pvc():
                core_v1.delete_namespaced_persistent_volume_claim(
                    name=pvc_name,
                    namespace=ns,
                )
                return f"deleted pvc {pvc_name}"

            async def step_scale_to_target():
                patch = {"spec": {"replicas": target_replicas}}
                apps_v1.patch_namespaced_stateful_set(
                    name=sts_name,
                    namespace=ns,
                    body=patch,
                )
                return f"scaled to {target_replicas}"

            async def step_wait_pods_ready():
                for _ in range(120):  # 最多等 10 分鐘
                    pods = core_v1.list_namespaced_pod(namespace=ns).items
                    related = [p for p in pods if p.metadata.name.startswith(f"{sts_name}-")]
                    if len(related) < target_replicas:
                        await asyncio.sleep(5)
                        continue

                    not_ready = []
                    for p in related:
                        conds = p.status.conditions or []
                        ready = any(
                            c.type == "Ready" and c.status == "True" for c in conds
                        )
                        if not ready:
                            not_ready.append(p.metadata.name)

                    if not not_ready:
                        return f"{len(related)} pods ready"

                    # 更新 detail
                    step_stmt = select(OpsJobStep).where(
                        OpsJobStep.job_id == job_id,
                        OpsJobStep.name == "wait_pods_ready"
                    )
                    step = db.scalar(step_stmt)
                    if step:
                        step.detail = f"not ready: {not_ready}"
                        db.commit()
                    await asyncio.sleep(5)
                raise RuntimeError("timeout waiting pods ready")

            # 執行步驟（跳過已成功的步驟）
            if "scale_sts_to_zero" not in completed_steps:
                await run_step("scale_sts_to_zero", step_scale_to_zero)
            if "wait_pods_down" not in completed_steps:
                await run_step("wait_pods_down", step_wait_pods_down)
            if "delete_pvc" not in completed_steps:
                await run_step("delete_pvc", step_delete_pvc)
            if "scale_sts_to_target" not in completed_steps:
                await run_step("scale_sts_to_target", step_scale_to_target)
            if "wait_pods_ready" not in completed_steps:
                await run_step("wait_pods_ready", step_wait_pods_ready)

            job.status = "success"
            job.finished_at = now_utc()
            db.commit()

        except Exception as e:
            print(f"[job {job_id}] error: {e}")

            # 自動重試邏輯
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = "pending"
                db.commit()

                print(f"[job {job_id}] retrying... (attempt {job.retry_count}/{job.max_retries})")

                # 等待 2 秒後重試（遞迴呼叫）
                await asyncio.sleep(2)
                await _run_pg_rebuild_job_async(job_id)
            else:
                # 達到最大重試次數
                print(f"[job {job_id}] max retries exceeded")
                job.status = "failed"
                job.finished_at = now_utc()
                db.commit()
