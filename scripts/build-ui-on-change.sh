#!/bin/bash
# フロントエンドファイル変更時に自動ビルドするフック
# PostToolUse で Edit/Write 実行後に呼び出される

# TOOL_INPUT から編集されたファイルパスを取得
FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"file_path":"[^"]*"' | sed 's/"file_path":"//;s/"$//')

# ファイルパスが取得できない場合は終了
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# 対象パターン: ui/src/ 以下の .svelte, .css, .ts ファイル
if echo "$FILE_PATH" | grep -qE 'ui/src/.*\.(svelte|css|ts)$'; then
    echo "UI file changed: $FILE_PATH"
    echo "Running build..."

    # プロジェクトルートを特定
    PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

    cd "$PROJECT_ROOT/ui" && bun run build

    if [ $? -eq 0 ]; then
        echo "Build completed successfully"
    else
        echo "Build failed"
        exit 1
    fi
fi

exit 0
