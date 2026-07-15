# Scripts

一時スクリプト・ユーティリティの一覧

| ファイル | 説明 |
|----------|------|
| `start.sh` | LocalDocSearch APIサーバー起動スクリプト |
| `install-daemon.sh` | launchdデーモンをインストール（ログインから150秒後に自動起動） |
| `uninstall-daemon.sh` | launchdデーモンをアンインストール |
| `com.localdocsearch.api.plist` | APIサーバー用launchd設定 |
| `com.localdocsearch.watcher.plist` | ファイル監視用launchd設定 |

## デーモンの使い方

### インストール

```bash
test -x /Users/ms25/.local/libexec/launchd-delay-exec
./scripts/install-daemon.sh
```

遅延ヘルパーは Dock プロセスの経過時間をログイン時刻の基準とし、150秒未満なら残り時間だけ待ちます。

### 状態確認

```bash
launchctl print gui/$(id -u)/com.localdocsearch.api
launchctl print gui/$(id -u)/com.localdocsearch.watcher
```

### ログ確認

```bash
tail -f ~/Library/Logs/local-doc-search/api.log
tail -f ~/Library/Logs/local-doc-search/watcher.log
```

### アンインストール

```bash
./scripts/uninstall-daemon.sh
```
