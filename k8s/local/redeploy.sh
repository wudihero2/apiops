#!/bin/bash
set -e

echo "=========================================="
echo "ApiOps Local Redeploy"
echo "=========================================="
echo ""

# 1. 重新建立 image
echo "🐳 步驟 1/4: 建立 Docker image..."
cd ../..
docker build -t apiops:local .
echo "✅ Image 建立完成"
echo ""

# 2. 載入到 kind cluster
echo "📦 步驟 2/4: 載入 image 到 kind cluster..."
kind load docker-image apiops:local --name apiops-dev
echo "✅ Image 已載入"
echo ""

# 3. 重啟 deployment
echo "🔄 步驟 3/4: 重啟 deployment..."
cd k8s/local
kubectl rollout restart deployment/apiops -n ops
echo "✅ Deployment 已重啟"
echo ""

# 4. 等待新 pod 啟動
echo "⏳ 步驟 4/4: 等待新 pod 啟動..."
kubectl rollout status deployment/apiops -n ops --timeout=120s
echo "✅ 新 pod 已啟動"
echo ""

echo "=========================================="
echo "🎉 重新部署完成！"
echo "=========================================="
echo ""
echo "📊 查看 logs："
echo "  kubectl logs -f -n ops -l app=apiops"
echo ""
