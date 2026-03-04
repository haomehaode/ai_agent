#!/bin/bash
# 在虚拟环境中运行 AI Agent
cd "$(dirname "$0")"
PYTHONPATH=. .venv/bin/python main_cli.py -i "$@"
