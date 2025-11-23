#!/bin/bash
set -e

echo "=========================================="
echo "ApiOps Local Environment Cleanup"
echo "=========================================="
echo ""

read -p "⚠️  確定要刪除 apiops-dev cluster 嗎? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 取消刪除"
    exit 0
fi

echo "🗑️  刪除 kind cluster..."
kind delete cluster --name apiops-dev

echo ""
echo "✅ 清理完成！"
echo ""
