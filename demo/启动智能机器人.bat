@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=gbk:replace
python wecom_robot.py
echo.
echo 智能机器人已退出。按任意键关闭。
pause
