# Job 開發指南

本指南說明如何使用 FastAPI BackgroundTasks 開發新的 Job 類型。

## 📋 目錄

1. [架構概述](#架構概述)
2. [BackgroundTasks vs asyncio.create_task](#backgroundtasks-vs-asynciocreate_task)
3. [開發新 Job 的步驟](#開發新-job-的步驟)
4. [範例：PG Rebuild Job](#範例pg-rebuild-job)
5. [最佳實踐](#最佳實踐)

---

## 架構概述

ApiOps 的 Job 系統架構：

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /ops/jobs/xxx
       ▼
┌─────────────────────────┐
│  FastAPI Route Handler  │
│  (app/routes/jobs.py)   │
└──────┬──────────────────┘
       │ 1. 建立 OpsJob & OpsJobStep 記錄
       │ 2. background_tasks.add_task()
       ▼
┌─────────────────────────┐
│  Background Job         │
│  (app/jobs/*.py)        │
│  - 執行實際操作         │
│  - 更新 step 狀態       │
└─────────────────────────┘
```

### 資料庫表格

- **ops_job**: 記錄 job 主要資訊
- **ops_job_step**: 記錄 job 的每個步驟

---

## BackgroundTasks vs asyncio.create_task

### 為什麼使用 BackgroundTasks？

✅ **FastAPI 官方推薦**
- 專為 FastAPI 設計的背景任務機制
- 文件：https://fastapi.tiangolo.com/tutorial/background-tasks/

✅ **更好的生命週期管理**
- 確保任務在 response 發送後才執行
- 自動處理 event loop

✅ **依賴注入支援**
- 可以注入其他 dependencies
- 程式碼更簡潔

✅ **測試友善**
- 更容易模擬和測試

### 對比

| 特性 | BackgroundTasks | asyncio.create_task |
|------|-----------------|---------------------|
| FastAPI 整合 | ✅ 原生支援 | ⚠️ 需手動處理 |
| 生命週期 | ✅ 自動管理 | ⚠️ 需手動管理 |
| Event Loop | ✅ 自動處理 | ⚠️ 可能衝突 |
| 依賴注入 | ✅ 支援 | ❌ 不支援 |
| 測試 | ✅ 容易 | ⚠️ 困難 |

---

## 開發新 Job 的步驟

### 步驟 1: 定義 Job 邏輯

在 `app/jobs/` 建立新檔案，例如 `my_job.py`：

```python
import asyncio
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import OpsJob, OpsJobStep
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

# 同步包裝函數（給 BackgroundTasks 使用）
def run_my_job(job_id: str):
    """
    同步包裝函數，用於 FastAPI BackgroundTasks。
    在新的 event loop 中執行 async job。
    """
    asyncio.run(_run_my_job_async(job_id))

# 實際的 async 邏輯
async def _run_my_job_async(job_id: str):
    """
    執行實際的 job 邏輯
    """
    db: Session = SessionLocal()
    try:
        job: OpsJob = db.query(OpsJob).filter_by(job_id=job_id).one()
        job.status = "running"
        db.commit()

        # 取得參數
        params = job.params

        # 執行各個步驟
        await _step_1(db, job_id, params)
        await _step_2(db, job_id, params)

        # 完成
        job.status = "success"
        job.finished_at = now_utc()
        db.commit()

    except Exception as e:
        print(f"[job {job_id}] error: {e}")
        job.status = "failed"
        job.finished_at = now_utc()
        db.commit()
    finally:
        db.close()

async def _step_1(db: Session, job_id: str, params: dict):
    """執行步驟 1"""
    step = db.query(OpsJobStep).filter_by(
        job_id=job_id,
        name="step_1"
    ).one()

    step.status = "running"
    step.started_at = now_utc()
    db.commit()

    try:
        # 實際操作
        await asyncio.sleep(1)  # 模擬操作

        step.status = "success"
        step.detail = "completed"
    except Exception as e:
        step.status = "failed"
        step.detail = f"error: {e}"
        raise
    finally:
        step.finished_at = now_utc()
        db.commit()
```

### 步驟 2: 建立 Pydantic Schema

在 `app/schemas.py` 加入請求 schema：

```python
class MyJobRequest(BaseModel):
    param1: str
    param2: int
```

### 步驟 3: 建立 API Endpoint

在 `app/routes/jobs.py` 加入新的 route：

```python
from ..jobs.my_job import run_my_job

@router.post("/jobs/my-job")
async def create_my_job(
    body: MyJobRequest,
    background_tasks: BackgroundTasks,  # 注入 BackgroundTasks
    request: Request,
    db: Session = Depends(get_db),
):
    # 驗證參數
    # ...

    # 建立 job 記錄
    job_id = gen_job_id("my-job")
    job = OpsJob(
        job_id=job_id,
        type="my-job",
        status="pending",
        created_at=now_utc(),
        params=body.dict(),
        actor=get_actor(request),
        source_ip=get_source_ip(request),
    )
    db.add(job)
    db.commit()

    # 建立 step 記錄
    steps_def = [
        ("step_1", 1),
        ("step_2", 2),
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

    # 加入背景任務（重點！）
    background_tasks.add_task(run_my_job, job_id)

    return {"job_id": job_id}
```

### 步驟 4: 更新 `__init__.py`

在 `app/jobs/__init__.py` 中 export：

```python
from .my_job import run_my_job  # noqa: F401
```

---

## 範例：PG Rebuild Job

完整的 PG Rebuild Job 實作可參考：

- Job 邏輯：[app/jobs/pg_rebuild.py](../app/jobs/pg_rebuild.py)
- API Route：[app/routes/jobs.py](../app/routes/jobs.py)

### 關鍵程式碼

#### 1. Job 函數（同步包裝）

```python
def run_pg_rebuild_job(job_id: str):
    """
    同步包裝函數，用於 FastAPI BackgroundTasks。
    """
    asyncio.run(_run_pg_rebuild_job_async(job_id))
```

#### 2. API Route（使用 BackgroundTasks）

```python
@router.post("/jobs/pg-rebuild")
async def create_pg_rebuild_job(
    body: PgRebuildRequest,
    background_tasks: BackgroundTasks,  # ← 注入 BackgroundTasks
    request: Request,
    db: Session = Depends(get_db),
):
    # ... 建立 job 記錄 ...

    # 使用 add_task 而非 asyncio.create_task
    background_tasks.add_task(run_pg_rebuild_job, job_id)

    return {"job_id": job_id}
```

---

## 最佳實踐

### 1. ✅ 使用同步包裝函數

```python
# ✅ 推薦：同步包裝
def run_my_job(job_id: str):
    asyncio.run(_run_my_job_async(job_id))

async def _run_my_job_async(job_id: str):
    # 實際 async 邏輯
    pass
```

**為什麼？**
- BackgroundTasks 對同步函數支援更好
- 避免 event loop 衝突
- 更穩定可靠

### 2. ✅ 總是使用 BackgroundTasks

```python
# ✅ 推薦
background_tasks.add_task(run_my_job, job_id)

# ❌ 避免
asyncio.create_task(run_my_job(job_id))
```

### 3. ✅ 獨立的資料庫 Session

```python
# ✅ 推薦：在 job 中建立新的 session
db = SessionLocal()
try:
    # 操作
    pass
finally:
    db.close()

# ❌ 避免：重用 route 的 db session
# 因為 background task 會在 response 後執行，session 可能已關閉
```

### 4. ✅ 完善的錯誤處理

```python
async def _run_my_job_async(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(OpsJob).filter_by(job_id=job_id).one()
        job.status = "running"
        db.commit()

        # 執行步驟
        await step_1()

        job.status = "success"
        job.finished_at = now_utc()
        db.commit()

    except Exception as e:
        # 記錄錯誤
        print(f"[job {job_id}] error: {e}")
        if 'job' in locals():
            job.status = "failed"
            job.finished_at = now_utc()
            db.commit()
    finally:
        db.close()
```

### 5. ✅ 步驟狀態追蹤

```python
async def _execute_step(db: Session, job_id: str, step_name: str, func):
    """通用的步驟執行包裝"""
    step = db.query(OpsJobStep).filter_by(
        job_id=job_id,
        name=step_name
    ).one()

    step.status = "running"
    step.started_at = now_utc()
    db.commit()

    try:
        detail = await func()
        step.status = "success"
        step.detail = detail
    except Exception as e:
        step.status = "failed"
        step.detail = f"error: {e}"
        raise
    finally:
        step.finished_at = now_utc()
        db.commit()
```

### 6. ✅ 適當的超時設定

```python
# 長時間等待加上超時
for i in range(120):  # 最多等 10 分鐘
    if condition_met():
        break
    await asyncio.sleep(5)
else:
    raise TimeoutError("operation timeout")
```

### 7. ✅ 詳細的進度更新

```python
# 在等待過程中更新步驟詳情
step.detail = f"waiting for pods, remaining: {pod_names}"
db.commit()
```

---

## 測試

### 單元測試範例

```python
from fastapi.testclient import TestClient
from app import create_app

client = TestClient(create_app())

def test_create_job():
    response = client.post(
        "/ops/jobs/my-job",
        headers={"X-API-Key": "test-key"},
        json={"param1": "value", "param2": 123}
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # 查詢 job 狀態
    response = client.get(f"/ops/jobs/{job_id}")
    assert response.status_code == 200
```

### 手動測試

```bash
# 建立 job
curl -X POST http://localhost:8080/ops/jobs/my-job \
  -H 'X-API-Key: dev-api-key-12345' \
  -H 'Content-Type: application/json' \
  -d '{"param1": "test", "param2": 42}'

# 查詢狀態
curl http://localhost:8080/ops/jobs/<job_id> \
  -H 'X-API-Key: dev-api-key-12345' | jq
```

---

## 常見問題

### Q: 為什麼要用同步包裝函數？

A: FastAPI 的 BackgroundTasks 會在獨立的執行緒池中執行任務。如果直接使用 async 函數，可能會遇到 event loop 相關的問題。使用 `asyncio.run()` 可以確保在新的 event loop 中執行。

### Q: 可以在 BackgroundTasks 中使用 dependencies 嗎？

A: 不能直接使用。BackgroundTasks 是在 response 發送後執行，此時 request context 已結束。需要手動傳遞必要的參數。

### Q: Job 失敗了怎麼辦？

A: 目前的設計不支援自動重試。可以：
1. 查看 `ops_job_step` 表找出失敗的步驟
2. 手動重新觸發 job
3. 或實作重試機制（待開發）

### Q: 如何監控 Job 執行？

A: 可以：
1. 查詢 `/ops/jobs/{job_id}` API
2. 查看資料庫 `ops_job` 和 `ops_job_step` 表
3. 查看應用 logs

---

## 參考資料

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SQLAlchemy Session](https://docs.sqlalchemy.org/en/14/orm/session.html)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
