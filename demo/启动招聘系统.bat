@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=gbk:replace
python app.py
echo.
echo Service stopped. Press any key to close.
pause
