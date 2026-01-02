# Scripts

一時スクリプト・ユーティリティの一覧

| ファイル | 説明 |
|----------|------|
| `start.sh` | LocalDocSearch APIサーバー起動スクリプト |
| `install-daemon.sh` | launchdデーモンをインストール（ログイン時自動起動） |
| `uninstall-daemon.sh` | launchdデーモンをアンインストール |
| `com.localdocsearch.api.plist` | APIサーバー用launchd設定 |
| `com.localdocsearch.watcher.plist` | ファイル監視用launchd設定 |

## デーモンの使い方

### インストール

```bash
./scripts/install-daemon.sh
```

### 状態確認

```bash
launchctl list | grep localdocsearch
```

### ログ確認

```bash
tail -f /tmp/localdocsearch-api.log
tail -f /tmp/localdocsearch-watcher.log
```

### アンインストール

```bash
./scripts/uninstall-daemon.sh
```
