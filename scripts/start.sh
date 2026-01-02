#!/bin/bash
# LocalDocSearch 起動スクリプト

set -e

# 色付きの出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}LocalDocSearch を起動します...${NC}"

# 作業ディレクトリをスクリプトの親ディレクトリに設定
cd "$(dirname "$0")/.."

# Ollama が起動しているか確認
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Ollama が起動していません。起動してください: ollama serve${NC}"
fi

# 必要なモデルの確認
echo -e "${GREEN}Ollama モデルを確認中...${NC}"
if ! ollama list | grep -q "bge-m3"; then
    echo -e "${YELLOW}bge-m3 モデルが見つかりません。インストール: ollama pull bge-m3${NC}"
fi

# API サーバーを起動
echo -e "${GREEN}API サーバーを起動中...${NC}"
uv run uvicorn src.api.main:app --host 127.0.0.1 --port 8765 &
API_PID=$!

# 終了時にプロセスをクリーンアップ
cleanup() {
    echo -e "\n${YELLOW}シャットダウン中...${NC}"
    kill $API_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# サーバーの起動を待つ
sleep 2

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}LocalDocSearch が起動しました!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "API: http://127.0.0.1:8765"
echo -e "API Docs: http://127.0.0.1:8765/docs"
echo ""
echo -e "Ctrl+C で終了"
echo ""

# プロセスを維持
wait $API_PID
