#!/usr/bin/env bash
# 一键启动后端+前端（Linux/macOS，从仓库根目录运行）
cd "$(dirname "$0")/.."
./scripts/start_backend.sh &
cd frontend
if [ ! -d node_modules ]; then npm install; fi
npm run dev
