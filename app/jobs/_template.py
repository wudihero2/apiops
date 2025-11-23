"""
Job Template

這是一個 job 範本，展示如何使用 FastAPI BackgroundTasks 開發新的 job。

使用方式：
1. 複製此檔案為新的 job 名稱，例如 my_job.py
2. 修改函數名稱和邏輯
3. 在 app/routes/jobs.py 建立對應的 API endpoint
4. 在 app/schemas.py 建立對應的 request schema
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import OpsJob, OpsJobStep


def now_utc():
    """取得當前 UTC 時間"""
    return datetime.now(timezone.utc)


def run_template_job(job_id: str):
    """
    同步包裝函數，用於 FastAPI BackgroundTasks。

    重要：BackgroundTasks 建議使用同步函數，
    內部透過 asyncio.run() 來執行 async 邏輯。

    Args:
        job_id: Job ID
    """
    asyncio.run(_run_template_job_async(job_id))


async def _run_template_job_async(job_id: str):
    """
    實際的 job 執行邏輯（async）。

    這個函數會：
    1. 更新 job 狀態為 running
    2. 執行各個步驟
    3. 更新每個 step 的狀態
    4. 完成後更新 job 狀態

    Args:
        job_id: Job ID
    """
    # 建立獨立的資料庫 session
    # 注意：不要重用 route handler 的 session，因為 background task
    # 會在 response 發送後執行，原本的 session 可能已關閉
    db: Session = SessionLocal()

    try:
        # 載入 job
        job: OpsJob = db.query(OpsJob).filter_by(job_id=job_id).one()
        job.status = "running"
        db.commit()

        # 取得參數
        params = job.params
        # 例如：
        # namespace = params["namespace"]
        # resource_name = params["resource_name"]

        # 執行步驟 1
        await _execute_step(
            db=db,
            job_id=job_id,
            step_name="step_1",
            func=lambda: _step_1(params),
        )

        # 執行步驟 2
        await _execute_step(
            db=db,
            job_id=job_id,
            step_name="step_2",
            func=lambda: _step_2(params),
        )

        # 執行步驟 3
        await _execute_step(
            db=db,
            job_id=job_id,
            step_name="step_3",
            func=lambda: _step_3(params),
        )

        # 所有步驟完成
        job.status = "success"
        job.finished_at = now_utc()
        db.commit()

    except Exception as e:
        # 錯誤處理
        print(f"[job {job_id}] error: {e}")

        # 更新 job 狀態
        if 'job' in locals():
            job.status = "failed"
            job.finished_at = now_utc()
            db.commit()

    finally:
        # 總是關閉資料庫連線
        db.close()


async def _execute_step(
    db: Session,
    job_id: str,
    step_name: str,
    func,
):
    """
    執行單個步驟的通用包裝函數。

    負責：
    1. 更新步驟狀態為 running
    2. 執行實際邏輯
    3. 處理錯誤
    4. 更新步驟狀態為 success/failed

    Args:
        db: Database session
        job_id: Job ID
        step_name: 步驟名稱
        func: 要執行的函數（應該是 async）
    """
    # 找出對應的 step 記錄
    step: OpsJobStep = (
        db.query(OpsJobStep)
        .filter_by(job_id=job_id, name=step_name)
        .one()
    )

    # 開始執行
    step.status = "running"
    step.started_at = now_utc()
    step.detail = None
    db.commit()

    try:
        # 執行實際邏輯，取得結果訊息
        detail = await func()

        # 成功
        step.status = "success"
        step.detail = detail
        step.finished_at = now_utc()
        db.commit()

    except Exception as e:
        # 失敗
        step.status = "failed"
        step.detail = f"error: {e}"
        step.finished_at = now_utc()
        db.commit()

        # 重新拋出例外，讓上層的 job 也標記為失敗
        raise


async def _step_1(params: dict) -> str:
    """
    步驟 1：做某件事

    Args:
        params: Job 參數

    Returns:
        步驟執行結果的描述文字
    """
    # 從參數取值
    # value = params.get("some_key")

    # 執行實際操作
    # 例如：呼叫 K8s API
    # core_v1.delete_namespaced_pod(...)

    # 如果需要等待，使用 await
    await asyncio.sleep(1)

    # 回傳結果描述
    return "step 1 completed successfully"


async def _step_2(params: dict) -> str:
    """
    步驟 2：等待某個條件

    Args:
        params: Job 參數

    Returns:
        步驟執行結果的描述文字
    """
    # 輪詢等待某個條件，設定超時
    max_attempts = 60  # 最多等 5 分鐘

    for attempt in range(max_attempts):
        # 檢查條件
        # if condition_met():
        #     return "condition met"

        # 未滿足，繼續等待
        await asyncio.sleep(5)

    # 超時
    raise TimeoutError("step 2 timeout after 5 minutes")


async def _step_3(params: dict) -> str:
    """
    步驟 3：完成某個操作

    Args:
        params: Job 參數

    Returns:
        步驟執行結果的描述文字
    """
    # 執行最後的操作

    return "step 3 completed"


# ============================================================================
# 在 app/routes/jobs.py 中使用此 job
# ============================================================================
#
# from fastapi import BackgroundTasks
# from ..jobs._template import run_template_job
#
# @router.post("/jobs/my-job")
# async def create_my_job(
#     body: MyJobRequest,
#     background_tasks: BackgroundTasks,  # ← 重要：注入 BackgroundTasks
#     request: Request,
#     db: Session = Depends(get_db),
# ):
#     # 建立 job 記錄
#     job_id = gen_job_id("my-job")
#     job = OpsJob(
#         job_id=job_id,
#         type="my-job",
#         status="pending",
#         created_at=now_utc(),
#         params=body.dict(),
#         actor=get_actor(request),
#         source_ip=get_source_ip(request),
#     )
#     db.add(job)
#     db.commit()
#
#     # 建立 step 記錄
#     steps_def = [
#         ("step_1", 1),
#         ("step_2", 2),
#         ("step_3", 3),
#     ]
#     for name, order in steps_def:
#         s = OpsJobStep(
#             job_id=job_id,
#             name=name,
#             step_order=order,
#             status="pending",
#         )
#         db.add(s)
#     db.commit()
#
#     # 加入背景任務
#     background_tasks.add_task(run_template_job, job_id)
#
#     return {"job_id": job_id}
