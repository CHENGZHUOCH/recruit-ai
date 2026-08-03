@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=gbk:replace
title 招聘数据管家 · 一键安装依赖

echo ================================================
echo   招聘数据管家 · 一键安装环境（新电脑只用一次）
echo ================================================
echo.

set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY py --version >nul 2>&1 && set "PY=py"
if not defined PY goto :no_python

echo [1/3] 检测到 Python:
%PY% --version
echo.

echo [2/3] 检查企业微信 SDK ...
%PY% -c "import aibot" >nul 2>&1
if errorlevel 1 goto :need_sdk
echo     已安装，跳过。
echo.
goto :check_config

:need_sdk
echo     未安装，正在通过清华镜像安装，请稍候...
%PY% -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple wecom-aibot-python-sdk
if errorlevel 1 goto :sdk_fail
echo     安装完成。
echo.

:check_config
echo [3/3] 检查机器人配置 ...
%PY% check_config.py >nul 2>&1
if errorlevel 1 goto :cfg_missing
echo     已就绪。
echo.
goto :done

:cfg_missing
echo     注意：未填 BotID/Secret，机器人收消息不可用（看板不受影响）。
echo     填写方法见《企业微信接入部署手册.md》第 4 节。
echo.

:done
echo ================================================
echo   全部就绪！以后每天开机：
echo   ① 双击「启动招聘系统.bat」   开看板服务
echo   ② 双击「启动智能机器人.bat」 收企业微信消息
echo   ③ 双击「查看看板.bat」      打开看板
echo   （本文件装完环境后即可不再使用）
echo ================================================
echo.
pause
exit /b 0

:no_python
echo.
echo   [*] 未检测到 Python！
echo.
echo   请先安装：
echo   ① 打开 https://www.python.org/downloads/
echo   ② 下载 Windows 版并安装
echo   ③ 安装时勾选「Add python.exe to PATH」 这步很重要！
echo   ④ 装好后重新双击本文件
echo.
pause
exit /b 1

:sdk_fail
echo.
echo   [*] SDK 安装失败，可能是网络问题。
echo   可稍后重试，或手动打开 cmd 运行：
echo     pip install -i https://pypi.tuna.tsinghua.edu.cn/simple wecom-aibot-python-sdk
echo.
pause
exit /b 1
