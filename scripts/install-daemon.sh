#!/bin/bash
# LocalDocSearch デーモンインストールスクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}LocalDocSearch デーモンをインストールします...${NC}"

# LaunchAgentsディレクトリを作成
mkdir -p "$LAUNCH_AGENTS_DIR"

# plistファイル内のパスを現在の環境に合わせて更新
update_plist() {
    local src="$1"
    local dest="$2"
    local venv_python="$PROJECT_DIR/.venv/bin/python"
    local venv_uvicorn="$PROJECT_DIR/.venv/bin/uvicorn"

    sed -e "s|/Users/ms25/project/local-doc-search|$PROJECT_DIR|g" \
        -e "s|/Users/ms25/Documents|$HOME/Documents|g" \
        "$src" > "$dest"
}

# APIサーバーのplistをインストール
echo -e "${GREEN}APIサーバーデーモンをインストール中...${NC}"
update_plist "$SCRIPT_DIR/com.localdocsearch.api.plist" "$LAUNCH_AGENTS_DIR/com.localdocsearch.api.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.localdocsearch.api.plist" 2>/dev/null || true

# ファイル監視デーモンのplistをインストール
echo -e "${GREEN}ファイル監視デーモンをインストール中...${NC}"
update_plist "$SCRIPT_DIR/com.localdocsearch.watcher.plist" "$LAUNCH_AGENTS_DIR/com.localdocsearch.watcher.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.localdocsearch.watcher.plist" 2>/dev/null || true

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}インストール完了!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "デーモン状態を確認:"
echo "  launchctl list | grep localdocsearch"
echo ""
echo "ログを確認:"
echo "  tail -f /tmp/localdocsearch-api.log"
echo "  tail -f /tmp/localdocsearch-watcher.log"
echo ""
echo "アンインストール:"
echo "  $SCRIPT_DIR/uninstall-daemon.sh"
