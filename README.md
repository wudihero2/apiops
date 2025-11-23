# ApiOps

Kubernetes 運維 API 服務，提供安全且可審計的 K8s 資源操作介面。

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
  "target_replicas": 1
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

1. 在 `app/jobs/` 建立新的 job 模組
2. 實作 async function 執行 job 邏輯
3. 在 `app/routes/jobs.py` 加入對應的 API endpoint
4. 更新 `app/jobs/__init__.py`

範例：
```python
# app/jobs/my_job.py
async def run_my_job(job_id: str):
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

## 安全注意事項

1. **API Key 管理**:
   - 生產環境必須使用強密碼
   - 定期輪換 API Key
   - 使用 Vault 或其他 secret 管理工具

2. **RBAC 最小權限**:
   - ServiceAccount 只授予必要的權限
   - 限制可操作的 namespace

3. **審計**:
   - 定期檢查 ops_log
   - 設定異常操作告警

4. **網路隔離**:
   - API 不應直接暴露在公網
   - 使用 VPN 或 bastion host 存取

## Roadmap

- [ ] 加入更多 Job 類型 (e.g., backup, restore)
- [ ] Webhook 通知 (Slack, Teams)
- [ ] Prometheus metrics
- [ ] Web UI (readonly dashboard)
- [ ] CLI tool (opsctl)
- [ ] 支援 dry-run mode
- [ ] Job 重試機制
- [ ] 操作審批流程

## License

MIT

## 貢獻

歡迎提交 PR 或開 issue！
