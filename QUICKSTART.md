# ApiOps 快速上手指南

## 5 分鐘啟動本地環境

### 1. 前置需求

```bash
# macOS
brew install docker kind kubectl

# 啟動 Docker Desktop
open -a Docker
```

### 2. 一鍵啟動

```bash
cd k8s/local
./setup.sh
```

等待 3-5 分鐘，看到 "🎉 設定完成！" 就成功了。

### 3. 測試 API

```bash
# 檢查健康狀態
curl http://localhost:8080/health/live

# 應該回傳: {"status":"ok"}
```

### 4. 第一個操作：Scale Deployment

```bash
# Scale test-app 到 3 replicas
curl -X POST http://localhost:8080/ops/namespaces/staging/deployments/test-app/scale \
  -H 'X-API-Key: dev-api-key-12345' \
  -H 'Content-Type: application/json' \
  -d '{"replicas": 3}'

# 驗證結果
kubectl get deployment test-app -n staging
# 應該看到 READY 3/3
```

### 5. 第一個 Job：PG Rebuild

```bash
# 建立 job
curl -X POST http://localhost:8080/ops/jobs/pg-rebuild \
  -H 'X-API-Key: dev-api-key-12345' \
  -H 'Content-Type: application/json' \
  -d '{
    "namespace": "prod",
    "statefulset": "test-pg",
    "ordinal": 0,
    "target_replicas": 1
  }'

# 會回傳 job_id，例如:
# {"job_id":"2025-01-15T10:30:00.000000+00:00_pg-rebuild_abc12345"}

# 查詢 job 狀態 (把 YOUR_JOB_ID 替換成上面回傳的值)
curl -H 'X-API-Key: dev-api-key-12345' \
  http://localhost:8080/ops/jobs/YOUR_JOB_ID | jq
```

### 6. 查看執行記錄

```bash
# 連到資料庫
kubectl exec -it -n ops deployment/postgres -- \
  psql -U apiops -d apiops

# 查詢最近的操作
SELECT ts, actor, action, resource_kind, namespace, resource_name, status
FROM ops_log
ORDER BY ts DESC
LIMIT 10;

# 查詢所有 jobs
SELECT job_id, type, status, created_at
FROM ops_job
ORDER BY created_at DESC;

# 離開資料庫
\q
```

## 常用指令

### 修改代碼後重新部署

```bash
cd k8s/local
./redeploy.sh
```

### 查看 API logs

```bash
kubectl logs -f -n ops -l app=apiops
```

### 重置環境

```bash
cd k8s/local
./teardown.sh
./setup.sh
```

## API 快速參考

### 認證

所有 API 都需要 header：
```
X-API-Key: dev-api-key-12345
```

### Endpoints

| 操作 | Method | Path |
|------|--------|------|
| 健康檢查 | GET | `/health/live` |
| Scale Deployment | POST | `/ops/namespaces/{ns}/deployments/{name}/scale` |
| Scale StatefulSet | POST | `/ops/namespaces/{ns}/statefulsets/{name}/scale` |
| Delete Pod | DELETE | `/ops/namespaces/{ns}/pods/{name}` |
| Delete PVC | DELETE | `/ops/namespaces/{ns}/persistentvolumeclaims/{name}` |
| 建立 PG Rebuild Job | POST | `/ops/jobs/pg-rebuild` |
| 查詢 Job 狀態 | GET | `/ops/jobs/{job_id}` |

### 測試資源

環境中已經建立了以下測試資源：

- **staging** namespace:
  - `test-app` Deployment (2 replicas)

- **prod** namespace:
  - `test-pg` StatefulSet (1 replica, 模擬 PostgreSQL)

## 下一步

- 閱讀 [README.md](README.md) 了解完整功能
- 閱讀 [k8s/local/README.md](k8s/local/README.md) 了解本地環境詳情
- 查看 [app/](app/) 目錄了解代碼結構
- 嘗試新增自己的 Job 類型

## 遇到問題？

### Pod 一直卡在 Pending

```bash
kubectl describe pod -n ops -l app=apiops
# 查看 Events 了解原因
```

### API 無法連線

```bash
# 確認 service 狀態
kubectl get svc -n ops

# 確認 pod 狀態
kubectl get pods -n ops

# 查看 logs
kubectl logs -n ops -l app=apiops --tail=50
```

### 完全重置

```bash
cd k8s/local
./teardown.sh
./setup.sh
```

## 聯絡方式

- 開 Issue: [GitHub Issues](https://github.com/your-repo/apiops/issues)
- 查看文件: [README.md](README.md)
