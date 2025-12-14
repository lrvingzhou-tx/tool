#!/usr/bin/env bash
# 简单的 Streamlit 启动脚本，支持通过环境变量 `PORT` 覆盖端口
set -euo pipefail

PORT="${PORT:-8501}"
ADDRESS="${ADDRESS:-0.0.0.0}"

echo "Starting Streamlit app on ${ADDRESS}:${PORT}..."
exec streamlit run ui/streamlimit_cal_ui.py --server.port "$PORT" --server.address "$ADDRESS"
