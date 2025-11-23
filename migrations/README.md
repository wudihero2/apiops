# Database Migrations

本目錄包含資料庫遷移腳本。

## 執行遷移

### 001: 新增 Job 重試欄位

此遷移新增了 `retry_count` 和 `max_retries` 欄位到 `ops_job` 表。

#### 執行方式

```bash
# 連線到資料庫
psql -h localhost -U ops_user -d ops_db

# 執行遷移
\i migrations/001_add_retry_fields.sql
```

#### 或使用 kubectl (在 Kubernetes 中)

```bash
# 找到 PostgreSQL pod
kubectl get pods -n ops-system

# 執行遷移
kubectl exec -it <postgres-pod> -n ops-system -- \
  psql -U ops_user -d ops_db -f /path/to/001_add_retry_fields.sql
```

#### 或手動執行 SQL

```sql
ALTER TABLE ops_job
ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE ops_job
ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3;

UPDATE ops_job
SET retry_count = 0, max_retries = 3
WHERE retry_count IS NULL OR max_retries IS NULL;
```

## 驗證遷移

```sql
-- 檢查欄位是否已建立
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'ops_job'
    AND column_name IN ('retry_count', 'max_retries');

-- 應該看到：
-- column_name  | data_type | column_default
-- -------------+-----------+----------------
-- retry_count  | integer   | 0
-- max_retries  | integer   | 3
```

## 回滾（如需要）

```sql
ALTER TABLE ops_job DROP COLUMN IF EXISTS retry_count;
ALTER TABLE ops_job DROP COLUMN IF EXISTS max_retries;
```
