#!/bin/bash
set -e

echo "=========================================="
echo "ApiOps Local Development Environment Setup"
echo "=========================================="
echo ""

# 檢查必要工具
echo "🔍 檢查必要工具..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker 未安裝，請先安裝 Docker"; exit 1; }
command -v kind >/dev/null 2>&1 || { echo "❌ kind 未安裝，請執行: brew install kind"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl 未安裝，請執行: brew install kubectl"; exit 1; }
echo "✅ 所有必要工具已安裝"
echo ""

# 1. 建立 kind cluster
echo "📦 步驟 1/7: 建立 kind cluster..."
if kind get clusters | grep -q "apiops-dev"; then
    echo "⚠️  Cluster apiops-dev 已存在"
    read -p "是否刪除並重建? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kind delete cluster --name apiops-dev
        kind create cluster --config kind-config.yaml
    fi
else
    kind create cluster --config kind-config.yaml
fi
echo "✅ Kind cluster 已就緒"
echo ""

# 2. 建立 namespaces
echo "📦 步驟 2/7: 建立 namespaces..."
kubectl create namespace ops --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace prod --dry-run=client -o yaml | kubectl apply -f -
echo "✅ Namespaces 已建立 (ops, staging, prod)"
echo ""

# 3. 部署 PostgreSQL
echo "📦 步驟 3/7: 部署 PostgreSQL..."
kubectl apply -f postgres.yaml
echo "⏳ 等待 PostgreSQL 啟動..."
kubectl wait --for=condition=ready pod -l app=postgres -n ops --timeout=120s
echo "✅ PostgreSQL 已啟動"
echo ""

# 4. 建立 ConfigMap 和 Secrets
echo "📦 步驟 4/7: 建立 ConfigMap 和 Secrets..."
kubectl apply -f configmap-secrets.yaml
echo "✅ ConfigMap 和 Secrets 已建立"
echo ""

# 5. 建立 RBAC
echo "📦 步驟 5/7: 建立 RBAC..."
kubectl apply -f rbac-local.yaml
echo "✅ RBAC 已設定"
echo ""

# 6. 建立 Docker image
echo "📦 步驟 6/7: 建立 Docker image..."
cd ../..
docker build -t apiops:local .
kind load docker-image apiops:local --name apiops-dev
cd k8s/local
echo "✅ Docker image 已載入 kind cluster"
echo ""

# 7. 部署 ApiOps
echo "📦 步驟 7/7: 部署 ApiOps..."
kubectl apply -f deployment-local.yaml
echo "⏳ 等待 ApiOps 啟動..."
kubectl wait --for=condition=ready pod -l app=apiops -n ops --timeout=120s || true
echo "✅ ApiOps 已部署"
echo ""

# 8. 部署測試 workloads
echo "📦 額外步驟: 部署測試 workloads..."
kubectl apply -f test-workloads.yaml
echo "✅ 測試 workloads 已部署"
echo ""

echo "=========================================="
echo "🎉 設定完成！"
echo "=========================================="
echo ""
echo "📝 連線資訊："
echo "  - ApiOps API: http://localhost:8080"
echo "  - PostgreSQL: localhost:5432"
echo "  - API Key: dev-api-key-12345"
echo ""
echo "🧪 測試指令："
echo "  # 檢查健康狀態"
echo "  curl http://localhost:8080/health/live"
echo ""
echo "  # 列出 staging namespace 的 pods"
echo "  curl -H 'X-API-Key: dev-api-key-12345' \\"
echo "       http://localhost:8080/ops/namespaces/staging/pods"
echo ""
echo "  # Scale deployment"
echo "  curl -X POST -H 'X-API-Key: dev-api-key-12345' \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"replicas\": 3}' \\"
echo "       http://localhost:8080/ops/namespaces/staging/deployments/test-app/scale"
echo ""
echo "  # 建立 PG rebuild job"
echo "  curl -X POST -H 'X-API-Key: dev-api-key-12345' \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"namespace\":\"prod\",\"statefulset\":\"test-pg\",\"ordinal\":0,\"target_replicas\":1}' \\"
echo "       http://localhost:8080/ops/jobs/pg-rebuild"
echo ""
echo "📊 查看 logs："
echo "  kubectl logs -f -n ops -l app=apiops"
echo ""
echo "🗄️  連線到 PostgreSQL："
echo "  psql -h localhost -p 5432 -U apiops -d apiops"
echo "  (密碼: dev-password-123)"
echo ""
echo "🧹 清理環境："
echo "  kind delete cluster --name apiops-dev"
echo ""
