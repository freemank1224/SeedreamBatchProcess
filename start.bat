@echo off
chcp 65001 >nul
title Seedream 批处理应用启动器

echo.
echo ================================================
echo 🎨 Seedream 批处理应用启动器
echo ================================================
echo.

cd /d "%~dp0"

echo 正在启动应用...
python scripts\start.py

pause