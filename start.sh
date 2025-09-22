#!/bin/bash

# Seedream 批处理应用启动脚本 (Linux/macOS)

# 设置脚本所在目录为工作目录
cd "$(dirname "$0")"

echo ""
echo "================================================"
echo "🎨 Seedream 批处理应用启动器"
echo "================================================"
echo ""

echo "正在启动应用..."
python3 scripts/start.py

echo ""
echo "应用已退出"
read -p "按回车键继续..."