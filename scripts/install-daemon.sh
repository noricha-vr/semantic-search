#!/bin/bash
# LocalDocSearch デーモンインストールスクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/local-doc-search"
DOMAIN="gui/$(id -u)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}LocalDocSearch デーモンをインストールします...${NC}"

# LaunchAgentsと非公開ログディレクトリを作成
mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p -m 700 "$LOG_DIR"
chmod 700 "$LOG_DIR"

xml_escape() {
    sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

sed_replacement_escape() {
    sed -e 's/[&|\\]/\\&/g'
}

escaped_replacement() {
    printf '%s' "$1" | xml_escape | sed_replacement_escape
}

# plistファイル内のパスを現在の環境に合わせて更新
update_plist() {
    local src="$1"
    local dest="$2"
    local project_dir home_dir log_dir
    project_dir="$(escaped_replacement "$PROJECT_DIR")"
    home_dir="$(escaped_replacement "$HOME")"
    log_dir="$(escaped_replacement "$LOG_DIR")"

    sed -e "s|__PROJECT_DIR__|$project_dir|g" \
        -e "s|__HOME__|$home_dir|g" \
        -e "s|__LOG_DIR__|$log_dir|g" \
        "$src" > "$dest"
    plutil -lint "$dest" >/dev/null
}

bootstrap_agent() {
    local label="$1"
    local plist="$2"

    launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$plist"
}

# APIサーバーのplistをインストール
echo -e "${GREEN}APIサーバーデーモンをインストール中...${NC}"
update_plist "$SCRIPT_DIR/com.localdocsearch.api.plist" "$LAUNCH_AGENTS_DIR/com.localdocsearch.api.plist"
bootstrap_agent "com.localdocsearch.api" "$LAUNCH_AGENTS_DIR/com.localdocsearch.api.plist"

# ファイル監視デーモンのplistをインストール
echo -e "${GREEN}ファイル監視デーモンをインストール中...${NC}"
update_plist "$SCRIPT_DIR/com.localdocsearch.watcher.plist" "$LAUNCH_AGENTS_DIR/com.localdocsearch.watcher.plist"
bootstrap_agent "com.localdocsearch.watcher" "$LAUNCH_AGENTS_DIR/com.localdocsearch.watcher.plist"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}インストール完了!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "デーモン状態を確認:"
echo "  launchctl print $DOMAIN/com.localdocsearch.api"
echo "  launchctl print $DOMAIN/com.localdocsearch.watcher"
echo ""
echo "ログを確認:"
echo "  tail -f $LOG_DIR/api.log"
echo "  tail -f $LOG_DIR/watcher.log"
echo ""
echo "アンインストール:"
echo "  $SCRIPT_DIR/uninstall-daemon.sh"
