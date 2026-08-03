@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=gbk:replace
python sync_tencent_docs.py
echo.
pause
