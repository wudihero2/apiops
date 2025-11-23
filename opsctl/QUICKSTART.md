# opsctl 快速上手指南

## 5 分鐘開始使用 opsctl

### 1. 安裝

```bash
cd opsctl
./install.sh
```

或手動安裝：

```bash
pip install -e .
```

### 2. 配置

```bash
# 本地開發環境
opsctl config set \
  --api-url http://localhost:8080 \
  --api-key dev-api-key-12345

# 驗證配置
opsctl config check
```

### 3. 第一個命令

```bash
# 健康檢查
opsctl health

# 應該看到：
# ✓ API is healthy
# {
#   "status": "ok"
# }
```

### 4. Scale 操作

```bash
# Scale deployment 到 3 個副本
opsctl scale deployment staging test-app 3

# 應該看到：
# ✓ Deployment scaling completed successfully
#   Namespace: staging
#   Deployment: test-app
#   Replicas: 3
```

### 5. 建立 Job

```bash
# 建立 PG rebuild job（預設重試 3 次）
opsctl job pg-rebuild \
  --namespace prod \
  --statefulset test-pg \
  --ordinal 0 \
  --yes

# 自訂最大重試次數
opsctl job pg-rebuild \
  --namespace prod \
  --statefulset test-pg \
  --ordinal 0 \
  --max-retries 5 \
  --yes

# 會回傳 job ID，例如：
# ✓ Job created: 2025-01-15T10:30:00+00:00_pg-rebuild_abc12345
```

### 6. 監控 Job

```bash
# 查詢一次
opsctl job status <job-id>

# Watch mode（即時更新）
opsctl job status <job-id> --watch
```

### 7. 重試失敗的 Job

```bash
# 手動重試失敗的 job
opsctl job retry <job-id>

# 跳過確認
opsctl job retry <job-id> -y
```

## 常用命令速查

### 配置

```bash
opsctl config set --api-url <url> --api-key <key>  # 設定配置
opsctl config show                                   # 查看配置
opsctl config check                                  # 檢查連線
```

### 健康檢查

```bash
opsctl health                                        # API 健康檢查
```

### Pod 操作

```bash
opsctl pod delete <namespace> <pod-name>             # 刪除 pod
opsctl pod delete <namespace> <pod-name> -y          # 跳過確認
```

### PVC 操作

```bash
opsctl pvc delete <namespace> <pvc-name>             # 刪除 PVC
opsctl pvc delete <namespace> <pvc-name> -y          # 跳過確認
```

### Scale 操作

```bash
opsctl scale deployment <ns> <name> <replicas>       # Scale deployment
opsctl scale statefulset <ns> <name> <replicas>      # Scale statefulset
```

### Job 操作

```bash
# 建立 PG rebuild job
opsctl job pg-rebuild -n <ns> -s <sts> -o <ord> -r <replicas>

# 建立 job 並指定最大重試次數
opsctl job pg-rebuild -n <ns> -s <sts> -o <ord> --max-retries 5

# 查詢 job 狀態
opsctl job status <job-id>

# Watch job 狀態（即時更新）
opsctl job status <job-id> -w

# 手動重試失敗的 job
opsctl job retry <job-id>
```

## 環境變數

也可以使用環境變數而不用配置檔案：

```bash
export OPSCTL_API_URL=http://localhost:8080
export OPSCTL_API_KEY=dev-api-key-12345

opsctl health
```

## 完整範例

```bash
# 1. 設定環境
export OPSCTL_API_URL=http://localhost:8080
export OPSCTL_API_KEY=dev-api-key-12345

# 2. 檢查連線
opsctl health

# 3. Scale deployment
opsctl scale deployment staging test-app 3

# 4. 建立 PG rebuild job 並監控
JOB_ID=$(opsctl job pg-rebuild -n prod -s test-pg -o 0 -y | grep "Job created" | awk '{print $4}')
opsctl job status $JOB_ID --watch
```

## 下一步

- 閱讀完整文件：[README.md](README.md)
- 查看範例腳本：[examples/](examples/)
- 了解 ApiOps：[../README.md](../README.md)
