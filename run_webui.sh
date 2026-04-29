#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未检测到 python3，请先安装 Python 3.10+"
  exit 1
fi

VENV_DIR="${VENV_DIR:-venv_webui}"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements_webui.txt >/dev/null

HOST="${WEBUI_HOST:-127.0.0.1}"
PORT="${WEBUI_PORT:-8000}"

echo "WebUI 启动中: http://${HOST}:${PORT}/"
echo "数据目录: ${PUBG_AFK_DATA_DIR:-$SCRIPT_DIR/data}"

exec python -m uvicorn webui.app:app --host "$HOST" --port "$PORT"

