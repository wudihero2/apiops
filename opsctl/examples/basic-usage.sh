#!/bin/bash

# opsctl 基本使用範例

# 設定 API endpoint 和 key
export OPSCTL_API_URL="http://localhost:8080"
export OPSCTL_API_KEY="dev-api-key-12345"

echo "=========================================="
echo "opsctl 基本使用範例"
echo "=========================================="
echo ""

# 健康檢查
echo "1. 健康檢查"
opsctl health
echo ""

# Scale deployment
echo "2. Scale deployment"
opsctl scale deployment staging test-app 3
echo ""

# 建立 PG rebuild job
echo "3. 建立 PG rebuild job"
opsctl job pg-rebuild \
  --namespace prod \
  --statefulset test-pg \
  --ordinal 0 \
  --target-replicas 1 \
  --yes
echo ""

# 提示：查詢 job 狀態
echo "提示：使用以下命令查詢 job 狀態"
echo "  opsctl job status <job-id>"
echo "  opsctl job status <job-id> --watch"
echo ""
