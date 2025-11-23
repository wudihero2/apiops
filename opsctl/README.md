# opsctl - ApiOps Command Line Tool

`opsctl` 是 ApiOps 的官方命令列工具，讓你可以透過簡單的命令操作 Kubernetes 資源。

## ✨ 功能

- 🔧 **原子操作**: Delete Pod, Delete PVC, Scale Deployment/StatefulSet
- 🤖 **Job 管理**: 建立和監控複雜的維運任務
- 🎨 **美化輸出**: 使用 Rich 提供清晰、彩色的輸出
- ⚙️ **配置管理**: 支援配置檔和環境變數
- 📊 **即時監控**: Watch mode 即時監控 Job 狀態

## 📦 安裝

### 從原始碼安裝

```bash
cd opsctl
pip install -e .
```

### 使用 pip 安裝（未來）

```bash
pip install opsctl
```

## 🚀 快速開始

### 1. 配置

首次使用需要設定 API endpoint 和 API key：

```bash
# 使用命令設定
opsctl config set --api-url http://localhost:8080 --api-key dev-api-key-12345

# 或使用環境變數
export OPSCTL_API_URL=http://localhost:8080
export OPSCTL_API_KEY=dev-api-key-12345
```

### 2. 驗證連線

```bash
opsctl config check
```

### 3. 測試基本命令

```bash
# 健康檢查
opsctl health

# 查看配置
opsctl config show
```

## 📖 使用說明

### 配置管理

```bash
# 設定配置
opsctl config set --api-url <url> --api-key <key>

# 查看配置
opsctl config show

# 檢查配置是否有效
opsctl config check
```

配置會儲存在 `~/.opsctl/config.yaml`。

### 健康檢查

```bash
opsctl health
```

### Pod 操作

```bash
# 刪除 pod
opsctl pod delete <namespace> <pod-name>

# 跳過確認
opsctl pod delete <namespace> <pod-name> --yes
```

### PVC 操作

```bash
# 刪除 PVC
opsctl pvc delete <namespace> <pvc-name>

# 跳過確認
opsctl pvc delete <namespace> <pvc-name> -y
```

### 擴縮容操作

```bash
# Scale Deployment
opsctl scale deployment <namespace> <name> <replicas>

# 範例：將 staging namespace 的 test-app scale 到 3
opsctl scale deployment staging test-app 3

# Scale StatefulSet
opsctl scale statefulset <namespace> <name> <replicas>

# 範例：將 prod namespace 的 postgres scale 到 0
opsctl scale statefulset prod postgres 0
```

### Job 操作

#### 建立 PG Rebuild Job

```bash
# 基本用法
opsctl job pg-rebuild \
  --namespace prod \
  --statefulset postgres \
  --ordinal 0 \
  --target-replicas 1

# 簡短寫法
opsctl job pg-rebuild -n prod -s postgres -o 0 -r 1

# 跳過確認
opsctl job pg-rebuild -n prod -s postgres -y
```

這個命令會：
1. Scale StatefulSet 到 0
2. 等待所有 pods 終止
3. 刪除指定的 PVC
4. Scale StatefulSet 到目標副本數
5. 等待 pods ready

#### 查詢 Job 狀態

```bash
# 查詢一次
opsctl job status <job-id>

# Watch mode（每 5 秒更新）
opsctl job status <job-id> --watch

# 簡短寫法
opsctl job status <job-id> -w
```

Watch mode 會自動清除螢幕並更新狀態，當 job 完成（success 或 failed）時自動停止。

## 🎨 輸出範例

### Job 狀態輸出

```
╭─────────────── Job Information ───────────────╮
│ Job ID: 2025-01-15T10:30:00+00:00_pg-rebuild │
│ Type: pg-rebuild                              │
│ Status: RUNNING                               │
│ Created: 2025-01-15 10:30:00 UTC             │
╰───────────────────────────────────────────────╯

╭───┬─────────────────────┬─────────┬──────────────┬──────────╮
│ # │ Step Name           │ Status  │ Detail       │ Duration │
├───┼─────────────────────┼─────────┼──────────────┼──────────┤
│ 1 │ scale_sts_to_zero   │ SUCCESS │ scaled to 0  │ 2s       │
│ 2 │ wait_pods_down      │ RUNNING │ waiting...   │ -        │
│ 3 │ delete_pvc          │ PENDING │ -            │ -        │
│ 4 │ scale_sts_to_target │ PENDING │ -            │ -        │
│ 5 │ wait_pods_ready     │ PENDING │ -            │ -        │
╰───┴─────────────────────┴─────────┴──────────────┴──────────╯
```

## 🔑 環境變數

- `OPSCTL_API_URL`: API endpoint URL
- `OPSCTL_API_KEY`: API key for authentication

環境變數會覆蓋配置檔中的設定。

## 📁 配置檔案

配置檔案位於 `~/.opsctl/config.yaml`：

```yaml
api_url: http://localhost:8080
api_key: dev-api-key-12345
```

## 🛠️ 開發

### 安裝開發依賴

```bash
cd opsctl
pip install -e ".[dev]"
```

### 執行測試

```bash
pytest
```

### 程式碼風格

```bash
black opsctl/
flake8 opsctl/
```

## 📝 常見問題

### Q: 如何更新配置？

A: 直接執行 `opsctl config set` 覆蓋即可，或手動編輯 `~/.opsctl/config.yaml`。

### Q: 可以同時管理多個環境嗎？

A: 目前版本僅支援單一配置。建議使用環境變數切換不同環境：

```bash
# Production
OPSCTL_API_URL=https://api.prod.example.com \
OPSCTL_API_KEY=prod-key \
opsctl health

# Staging
OPSCTL_API_URL=https://api.staging.example.com \
OPSCTL_API_KEY=staging-key \
opsctl health
```

### Q: 如何取得 API Key？

A: API Key 由 ApiOps 管理員提供。本地開發環境的預設 key 是 `dev-api-key-12345`。

### Q: Watch mode 沒有正確更新？

A: 確保你的終端支援 ANSI 色碼。部分舊版終端可能不支援清除螢幕功能。

## 🔗 相關連結

- [ApiOps 主專案](../README.md)
- [Job 開發指南](../docs/JOB_DEVELOPMENT_GUIDE.md)
- [安全檢查清單](../.security-checklist.md)

## 📄 授權

MIT License

## 🤝 貢獻

歡迎提交 PR 或開 Issue！
