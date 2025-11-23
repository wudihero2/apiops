# ApiOps Local Development Environment

使用 kind (Kubernetes IN Docker) 在本地電腦建立完整的 ApiOps 開發環境。

## ⚠️ 安全警告

**此目錄僅供本地開發使用！**

- ❌ **絕對不可**將此目錄中的配置用於生產環境
- ❌ **絕對不可**將開發用密碼用於任何真實環境
- ✅ 生產環境請使用 Vault 管理 secrets
- ✅ 生產環境請使用強密碼（至少 32 字元）

本目錄中的密碼（如 `dev-password-123`、`dev-api-key-12345`）僅供本地 kind cluster 使用，不具備任何安全性。

## 前置需求

在開始之前，請確保已安裝以下工具：

```bash
# macOS
brew install docker kind kubectl

# 或手動安裝
# - Docker Desktop: https://www.docker.com/products/docker-desktop
# - kind: https://kind.sigs.k8s.io/docs/user/quick-start/
# - kubectl: https://kubernetes.io/docs/tasks/tools/
```

確認工具已安裝：
```bash
docker --version
kind --version
kubectl version --client
```

## 快速開始

### 一鍵安裝

```bash
cd k8s/local
./setup.sh
```

這個腳本會自動完成以下步驟：
1. ✅ 檢查必要工具
2. 📦 建立 kind cluster
3. 🏗️ 建立 namespaces (ops, staging, prod)
4. 🗄️ 部署 PostgreSQL 資料庫
5. 🔐 建立 ConfigMap 和 Secrets
6. 👤 設定 RBAC 權限
7. 🐳 建立並載入 Docker image
8. 🚀 部署 ApiOps 服務
9. 🧪 部署測試 workloads

### 手動安裝步驟

如果想要手動執行，可以按照以下步驟：

#### 1. 建立 kind cluster

```bash
kind create cluster --config kind-config.yaml
```

#### 2. 建立 namespaces

```bash
kubectl create namespace ops
kubectl create namespace staging
kubectl create namespace prod
```

#### 3. 部署 PostgreSQL

```bash
kubectl apply -f postgres.yaml
kubectl wait --for=condition=ready pod -l app=postgres -n ops --timeout=120s
```

#### 4. 建立配置

```bash
kubectl apply -f configmap-secrets.yaml
kubectl apply -f rbac-local.yaml
```

#### 5. 建立並載入 Docker image

```bash
# 回到專案根目錄
cd ../..

# 建立 image
docker build -t apiops:local .

# 載入到 kind cluster
kind load docker-image apiops:local --name apiops-dev

# 回到 local 目錄
cd k8s/local
```

#### 6. 部署 ApiOps

```bash
kubectl apply -f deployment-local.yaml
kubectl wait --for=condition=ready pod -l app=apiops -n ops --timeout=120s
```

#### 7. 部署測試 workloads

```bash
kubectl apply -f test-workloads.yaml
```

## 架構說明

### 網路配置

- **ApiOps API**: `http://localhost:8080`
  - 對應 kind cluster 的 NodePort 30080
- **PostgreSQL**: `localhost:5432`
  - 對應 kind cluster 的 NodePort 30543

### Namespaces

- **ops**: ApiOps 本身和 PostgreSQL
- **staging**: 測試環境 (包含一個 test-app Deployment)
- **prod**: 生產環境 (包含一個 test-pg StatefulSet)

### 認證資訊

- **API Key**: `dev-api-key-12345`
- **PostgreSQL**:
  - User: `apiops`
  - Password: `dev-password-123`
  - Database: `apiops`

## 測試 API

### 1. 檢查服務健康狀態

```bash
# Liveness probe
curl http://localhost:8080/health/live

# Readiness probe
curl http://localhost:8080/health/ready

# 根路徑
curl http://localhost:8080/
```

### 2. 測試原子操作

#### Scale Deployment

```bash
curl -X POST http://localhost:8080/ops/namespaces/staging/deployments/test-app/scale \
  -H 'X-API-Key: dev-api-key-12345' \
  -H 'Content-Type: application/json' \
  -d '{"replicas": 3}'
```

驗證：
```bash
kubectl get deployment test-app -n staging
```

#### Scale StatefulSet

```bash
curl -X POST http://localhost:8080/ops/namespaces/prod/statefulsets/test-pg/scale \
  -H 'X-API-Key: dev-api-key-12345' \
  -H 'Content-Type: application/json' \
  -d '{"replicas": 0}'
```

驗證：
```bash
kubectl get statefulset test-pg -n prod
```

#### Delete Pod

```bash
# 先找到一個 pod
kubectl get pods -n staging

# 刪除 pod
curl -X DELETE http://localhost:8080/ops/namespaces/staging/pods/test-app-xxx-yyy \
  -H 'X-API-Key: dev-api-key-12345'
```

#### Delete PVC

```bash
# 列出 PVC
kubectl get pvc -n prod

# 刪除 PVC (注意：需要先 scale StatefulSet 到 0)
curl -X DELETE http://localhost:8080/ops/namespaces/prod/persistentvolumeclaims/data-test-pg-0 \
  -H 'X-API-Key: dev-api-key-12345'
```

### 3. 測試 Job 系統

#### 建立 PG Rebuild Job

```bash
# 建立 job
JOB_RESPONSE=$(curl -s -X POST http://localhost:8080/ops/jobs/pg-rebuild \
  -H 'X-API-Key: dev-api-key-12345' \
  -H 'Content-Type: application/json' \
  -d '{
    "namespace": "prod",
    "statefulset": "test-pg",
    "ordinal": 0,
    "target_replicas": 1
  }')

echo $JOB_RESPONSE
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"
```

#### 查詢 Job 狀態

```bash
# 持續查詢 job 狀態
watch -n 2 "curl -s http://localhost:8080/ops/jobs/$JOB_ID \
  -H 'X-API-Key: dev-api-key-12345' | jq"
```

Job 會執行以下步驟：
1. Scale StatefulSet → 0
2. 等待所有 pods down
3. 刪除 PVC
4. Scale StatefulSet → target_replicas
5. 等待 pods ready

## 查看 Logs 和狀態

### ApiOps Logs

```bash
# 即時查看 logs
kubectl logs -f -n ops -l app=apiops

# 查看最近 100 行
kubectl logs --tail=100 -n ops -l app=apiops
```

### PostgreSQL Logs

```bash
kubectl logs -f -n ops -l app=postgres
```

### 查看資料庫內容

```bash
# 連線到 PostgreSQL
kubectl exec -it -n ops deployment/postgres -- psql -U apiops -d apiops

# 或從本機連線
psql -h localhost -p 5432 -U apiops -d apiops
# 密碼: dev-password-123
```

在 PostgreSQL 中查詢：
```sql
-- 查看所有操作 log
SELECT * FROM ops_log ORDER BY ts DESC LIMIT 10;

-- 查看所有 jobs
SELECT * FROM ops_job ORDER BY created_at DESC;

-- 查看特定 job 的 steps
SELECT * FROM ops_job_step WHERE job_id = 'your-job-id' ORDER BY step_order;
```

### 查看所有資源

```bash
# 查看 ops namespace
kubectl get all -n ops

# 查看 staging namespace
kubectl get all -n staging

# 查看 prod namespace
kubectl get all -n prod
```

## 開發流程

### 修改代碼後重新部署

```bash
# 1. 重新建立 image
cd ../..
docker build -t apiops:local .

# 2. 載入到 kind cluster
kind load docker-image apiops:local --name apiops-dev

# 3. 重啟 deployment
kubectl rollout restart deployment/apiops -n ops

# 4. 等待新 pod 啟動
kubectl rollout status deployment/apiops -n ops

# 5. 查看 logs
kubectl logs -f -n ops -l app=apiops
```

或使用一鍵腳本：
```bash
cd k8s/local
./redeploy.sh  # (需要另外建立此腳本)
```

### 本機開發模式 (不使用 K8s)

如果只是要測試 API 邏輯，可以直接在本機跑：

```bash
# 設定環境變數
export OPS_API_KEY="dev-api-key-12345"
export OPS_DB_URL="postgresql://apiops:dev-password-123@localhost:5432/apiops"
export ENV="local"

# 確保 PostgreSQL 在 kind 中運行並 port-forward
kubectl port-forward -n ops svc/postgres 5432:5432 &

# 啟動 API (開發模式)
cd ../..
pip install -r requirements.txt
python main.py

# API 會在 http://localhost:8000 啟動
```

## 故障排除

### Pod 無法啟動

```bash
# 查看 pod 狀態
kubectl get pods -n ops

# 查看詳細資訊
kubectl describe pod <pod-name> -n ops

# 查看 logs
kubectl logs <pod-name> -n ops
```

### Image 無法載入

```bash
# 確認 image 存在
docker images | grep apiops

# 重新載入
kind load docker-image apiops:local --name apiops-dev

# 確認 kind cluster 中的 images
docker exec -it apiops-dev-control-plane crictl images | grep apiops
```

### 無法連線到 API

```bash
# 確認 port-forward 正常
kubectl get svc -n ops

# 檢查 NodePort
kubectl get svc apiops -n ops -o jsonpath='{.spec.ports[0].nodePort}'

# 測試從 cluster 內部連線
kubectl run -it --rm test --image=curlimages/curl --restart=Never -- \
  curl http://apiops.ops.svc.cluster.local/health/live
```

### PostgreSQL 連線問題

```bash
# 檢查 PostgreSQL pod
kubectl get pod -n ops -l app=postgres

# 測試連線
kubectl exec -it -n ops deployment/postgres -- psql -U apiops -d apiops -c '\dt'
```

### 重新開始

如果遇到無法解決的問題，可以完全重置：

```bash
# 刪除 cluster
./teardown.sh

# 重新建立
./setup.sh
```

## 清理環境

### 刪除所有資源

```bash
./teardown.sh
```

或手動刪除：
```bash
kind delete cluster --name apiops-dev
```

### 僅刪除 ApiOps (保留 cluster)

```bash
kubectl delete -f deployment-local.yaml
kubectl delete -f configmap-secrets.yaml
```

## 檔案說明

- `kind-config.yaml`: kind cluster 設定檔，定義 port mapping
- `postgres.yaml`: PostgreSQL 部署設定
- `configmap-secrets.yaml`: 本地開發用的配置和 secrets
- `rbac-local.yaml`: RBAC 權限設定 (支援 ops/staging/prod)
- `deployment-local.yaml`: ApiOps 本地部署設定
- `test-workloads.yaml`: 測試用的 workloads
- `setup.sh`: 一鍵安裝腳本
- `teardown.sh`: 清理腳本
- `README.md`: 本說明文件

## 注意事項

1. **本地開發專用**: 這個環境僅供本地開發測試，不適用於生產環境
2. **資料不持久化**: 刪除 cluster 後所有資料會遺失
3. **預設認證資訊**: API Key 和資料庫密碼都是硬編碼，僅供開發使用
4. **資源限制**: kind cluster 受限於本機 Docker 資源
5. **沒有 Vault**: 本地環境使用 ConfigMap/Secret，生產環境才用 Vault

## 進階用法

### 模擬多節點 cluster

修改 `kind-config.yaml`:
```yaml
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

### 啟用 Ingress

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

### 連接本地 registry

參考 kind 官方文件：
https://kind.sigs.k8s.io/docs/user/local-registry/

## 相關連結

- [kind 官方文件](https://kind.sigs.k8s.io/)
- [kubectl 參考](https://kubernetes.io/docs/reference/kubectl/)
- [FastAPI 文件](https://fastapi.tiangolo.com/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
