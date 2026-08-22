#!/usr/bin/env bash
# 后端一键启动（Linux/macOS，从仓库根目录运行）
set -e
cd "$(dirname "$0")/../backend"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f data/app.db ]; then python -m scripts.seed; fi
if [ ! -f .env ]; then cp .env.example .env; fi
uvicorn app.main:app --reload --port 8000
