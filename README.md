# ApiOps

Kubernetes 運維 API 服務，提供安全且可審計的 K8s 資源操作介面。

## 🔒 安全須知

- **開發環境**: `k8s/local/` 目錄包含僅供本地開發的測試密碼，絕不可用於生產環境
- **生產環境**: 必須使用 Vault 管理 secrets，使用強密碼（至少 32 字元）
- **密碼外露**: 本 repo 不包含任何真實密碼，所有硬編碼密碼都僅供本地測試
- **安全審計**: 詳見 [SECURITY_AUDIT.md](SECURITY_AUDIT.md)

## 特色功能

### 1. 原子級操作 API

提供基礎的 Kubernetes 資源操作：

- **Pod 管理**: 刪除 pod
- **PVC 管理**: 刪除 PersistentVolumeClaim
- **擴縮容**: Scale Deployment/StatefulSet

所有操作都會記錄到 `ops_log` 表，包含：
- 操作者 (actor)
- 來源 IP
- 操作類型、資源、參數
- 執行結果

### 2. Job 編排系統

複雜操作透過 Job 系統執行，支援：

- **異步執行**: 背景處理長時間任務
- **步驟追蹤**: 每個 job 包含多個 step，可獨立追蹤狀態
- **進度查詢**: 透過 API 查詢 job 執行進度
- **自動重試**: Job 失敗時自動重試，從失敗步驟繼續執行（預設 3 次）
- **手動重試**: 透過 API 或 CLI 手動觸發重試

**範例 Job: PostgreSQL Rebuild**

自動化 PG pod rebuild 流程：
1. Scale StatefulSet → 0
2. 等待所有 pods down
3. 刪除指定的 PVC
4. Scale StatefulSet → target replicas
5. 等待 pods ready

### 3. 安全性

- **API Key 認證**: 所有 API 都需要 X-API-Key header
- **Namespace 白名單**: 只能操作允許的 namespace
- **RBAC 整合**: 使用 ServiceAccount 控制 K8s 權限
- **Vault 整合**: 生產環境使用 Vault 管理 secrets

### 4. 審計追蹤

- 所有操作記錄到 PostgreSQL
- 追蹤操作者、時間、參數、結果
- Job 系統記錄每個步驟的詳細狀態

## 快速開始

### 本地開發環境

使用 kind 在本機建立完整的開發環境：

```bash
cd k8s/local
./setup.sh
```

詳細說明請見 [k8s/local/README.md](k8s/local/README.md)

### 生產環境部署

1. **準備 Vault secrets**:
   ```bash
   # 在 Vault 中建立 secrets
   vault kv put secret/ops-api api_key="your-secure-api-key"
   vault kv put secret/ops-api-db db_url="postgresql://user:pass@host:5432/dbname"
   ```

2. **建立 Docker image**:
   ```bash
   docker build -t your-registry/apiops:v1.0.0 .
   docker push your-registry/apiops:v1.0.0
   ```

3. **更新 K8s manifests**:
   - 修改 `k8s/deployment.yaml` 中的 image
   - 修改 Vault annotations 以符合你的 Vault 設定

4. **部署到 K8s**:
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/serviceaccount-rbac.yaml
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```

## API 文件

### 認證

所有 API 都需要在 header 中帶入 API Key：

```bash
curl -H "X-API-Key: your-api-key" http://api-host/endpoint
```

### Health Check

```bash
GET /health/live   # Liveness probe
GET /health/ready  # Readiness probe
```

### 原子操作

#### Scale Deployment

```bash
POST /ops/namespaces/{namespace}/deployments/{name}/scale
Content-Type: application/json
X-API-Key: xxx

{
  "replicas": 3
}
```

#### Scale StatefulSet

```bash
POST /ops/namespaces/{namespace}/statefulsets/{name}/scale
Content-Type: application/json
X-API-Key: xxx

{
  "replicas": 1
}
```

#### Delete Pod

```bash
DELETE /ops/namespaces/{namespace}/pods/{pod_name}
X-API-Key: xxx
```

#### Delete PVC

```bash
DELETE /ops/namespaces/{namespace}/persistentvolumeclaims/{pvc_name}
X-API-Key: xxx
```

### Job 操作

#### 建立 PG Rebuild Job

```bash
POST /ops/jobs/pg-rebuild
Content-Type: application/json
X-API-Key: xxx

{
  "namespace": "prod",
  "statefulset": "postgres",
  "ordinal": 0,
  "target_replicas": 1,
  "max_retries": 3  # 可選，預設 3
}

# Response
{
  "job_id": "2025-01-15T10:30:00+00:00_pg-rebuild_abc12345"
}
```

#### 查詢 Job 狀態

```bash
GET /ops/jobs/{job_id}
X-API-Key: xxx

# Response
{
  "job_id": "...",
  "type": "pg-rebuild",
  "status": "running",  # pending / running / success / failed
  "created_at": "2025-01-15T10:30:00Z",
  "finished_at": null,
  "params": {...},
  "retry_count": 0,
  "max_retries": 3,
  "steps": [
    {
      "name": "scale_sts_to_zero",
      "order": 1,
      "status": "success",
      "detail": "scaled to 0",
      "started_at": "2025-01-15T10:30:01Z",
      "finished_at": "2025-01-15T10:30:02Z"
    },
    ...
  ]
}
```

#### 手動重試 Job

```bash
POST /ops/jobs/{job_id}/retry
X-API-Key: xxx

# Response
{
  "message": "job retry scheduled",
  "job_id": "...",
  "retry_count": 1,
  "max_retries": 3
}
```

## 專案結構

```
apiops/
├── app/
│   ├── __init__.py          # FastAPI app factory
│   ├── config.py            # 設定 (Vault 整合)
│   ├── db.py                # SQLAlchemy 設定
│   ├── k8s_client.py        # K8s client
│   ├── auth.py              # API Key 驗證
│   ├── models.py            # DB models
│   ├── schemas.py           # Pydantic schemas
│   ├── logging_utils.py     # 操作記錄
│   ├── jobs/                # Job 定義
│   │   └── pg_rebuild.py
│   └── routes/              # API routes
│       ├── health.py
│       ├── ops_primitive.py
│       └── jobs.py
├── k8s/                     # K8s manifests
│   ├── namespace.yaml
│   ├── serviceaccount-rbac.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── local/               # 本地開發環境
│       ├── README.md
│       ├── setup.sh
│       └── ...
├── main.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## 資料庫 Schema

### ops_log

所有原子操作的記錄：

```sql
CREATE TABLE ops_log (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    actor TEXT,
    source_ip TEXT,
    action TEXT NOT NULL,
    resource_kind TEXT NOT NULL,
    namespace TEXT NOT NULL,
    resource_name TEXT NOT NULL,
    request_body JSONB,
    status TEXT NOT NULL,  -- 'success' / 'error'
    error_message TEXT
);
```

### ops_job

Job 主表：

```sql
CREATE TABLE ops_job (
    id BIGSERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'pending' / 'running' / 'success' / 'failed'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    params JSONB NOT NULL,
    actor TEXT,
    source_ip TEXT
);
```

### ops_job_step

Job 步驟明細：

```sql
CREATE TABLE ops_job_step (
    id BIGSERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    name TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    status TEXT NOT NULL,  -- 'pending' / 'running' / 'success' / 'failed'
    detail TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE
);
```

## 開發指南

### 新增 Job 類型

ApiOps 使用 **FastAPI BackgroundTasks** 來處理背景任務。

📖 **完整指南**: [docs/JOB_DEVELOPMENT_GUIDE.md](docs/JOB_DEVELOPMENT_GUIDE.md)
📄 **範本檔案**: [app/jobs/_template.py](app/jobs/_template.py)

快速開始：

```python
# app/jobs/my_job.py
import asyncio

def run_my_job(job_id: str):
    """同步包裝函數，用於 BackgroundTasks"""
    asyncio.run(_run_my_job_async(job_id))

async def _run_my_job_async(job_id: str):
    """實際的 async 邏輯"""
    db = SessionLocal()
    try:
        job = db.query(OpsJob).filter_by(job_id=job_id).one()
        job.status = "running"
        db.commit()
        # 執行邏輯...
        job.status = "success"
        job.finished_at = now_utc()
        db.commit()
    finally:
        db.close()

# app/routes/jobs.py
from fastapi import BackgroundTasks

@router.post("/jobs/my-job")
async def create_my_job(
    background_tasks: BackgroundTasks,  # ← 注入
    ...
):
    background_tasks.add_task(run_my_job, job_id)  # ← 使用 add_task
    return {"job_id": job_id}
```

### 新增原子操作

在 `app/routes/ops_primitive.py` 加入新的 endpoint：

```python
@router.post("/namespaces/{namespace}/my-operation")
def my_operation(
    namespace: str,
    request: Request,
    db: Session = Depends(get_db),
):
    ensure_ns(namespace)
    status = "error"
    err = None
    try:
        # 執行 K8s 操作
        status = "success"
        return {"status": "ok"}
    except Exception as e:
        err = str(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        safe_log_op(db, request=request, ...)
```

## 配置

### 環境變數

- `ENV`: 環境名稱 (local/staging/prod)
- `OPS_API_KEY`: API Key (或由 Vault 注入)
- `OPS_DB_URL`: PostgreSQL 連線字串 (或由 Vault 注入)

### Vault 整合 (生產環境)

Vault Agent 會將 secrets 注入到 `/vault/secrets/` 目錄：
- `/vault/secrets/api-key`: API Key
- `/vault/secrets/db-url`: 資料庫連線字串

### Namespace 白名單

在 `app/config.py` 設定：
```python
ALLOWED_NAMESPACES: set[str] = {"prod", "staging"}
```

## 監控與除錯

### 查看 Logs

```bash
kubectl logs -f -n ops -l app=apiops
```

### 查看 Database

```bash
kubectl exec -it -n ops deployment/postgres -- psql -U apiops

# 查詢操作記錄
SELECT * FROM ops_log ORDER BY ts DESC LIMIT 20;

# 查詢 job 狀態
SELECT * FROM ops_job WHERE status = 'running';
```

### Metrics

TODO: 加入 Prometheus metrics

## CLI Tool

ApiOps 提供 `opsctl` 命令列工具，讓你可以透過終端操作 API。

### 安裝

```bash
cd opsctl
./install.sh
```

### 快速開始

```bash
# 配置
opsctl config set --api-url http://localhost:8080 --api-key dev-api-key-12345

# 健康檢查
opsctl health

# Scale deployment
opsctl scale deployment staging test-app 3

# 建立 PG rebuild job
opsctl job pg-rebuild -n prod -s test-pg -o 0 -y

# 監控 job（即時更新）
opsctl job status <job-id> --watch
```

詳細文件請見：[opsctl/README.md](opsctl/README.md)

## Roadmap

- [x] CLI tool (opsctl) ✅
- [ ] 加入更多 Job 類型 (e.g., backup, restore)
- [ ] Webhook 通知 (Slack, Teams)
- [ ] Prometheus metrics
- [ ] Web UI (readonly dashboard)
- [ ] 支援 dry-run mode
- [ ] Job 重試機制
- [ ] 操作審批流程
