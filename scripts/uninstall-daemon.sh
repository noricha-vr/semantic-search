#!/bin/bash
# LocalDocSearch デーモンアンインストールスクリプト

set -e

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${RED}LocalDocSearch デーモンをアンインストールします...${NC}"

# APIサーバーデーモンを停止・削除
if [ -f "$LAUNCH_AGENTS_DIR/com.localdocsearch.api.plist" ]; then
    echo "APIサーバーデーモンを停止中..."
    launchctl unload "$LAUNCH_AGENTS_DIR/com.localdocsearch.api.plist" 2>/dev/null || true
    rm -f "$LAUNCH_AGENTS_DIR/com.localdocsearch.api.plist"
fi

# ファイル監視デーモンを停止・削除
if [ -f "$LAUNCH_AGENTS_DIR/com.localdocsearch.watcher.plist" ]; then
    echo "ファイル監視デーモンを停止中..."
    launchctl unload "$LAUNCH_AGENTS_DIR/com.localdocsearch.watcher.plist" 2>/dev/null || true
    rm -f "$LAUNCH_AGENTS_DIR/com.localdocsearch.watcher.plist"
fi

echo ""
echo -e "${GREEN}アンインストール完了!${NC}"
