@echo off
chcp 65001 >nul
setlocal
title 말씀 PPT 변환기

rem 소스에서 바로 실행하는 스크립트입니다. 필요한 것은 Node.js 하나뿐입니다.
rem (Python은 앱 전용으로 electron_app_py\python-runtime 폴더에 자동으로 받습니다)

cd /d "%~dp0electron_app_py"
if errorlevel 1 goto :no_folder

where node >nul 2>nul
if errorlevel 1 goto :no_node

if exist "node_modules\electron\dist\electron.exe" goto :prepare_python

echo.
echo  처음 실행 준비 중입니다. 인터넷 연결이 필요하며 몇 분 걸릴 수 있습니다...
echo.
call npm install --no-audit --no-fund
if errorlevel 1 goto :install_failed
goto :launch

:prepare_python
node scripts\prepare-python.js
if errorlevel 1 goto :install_failed

:launch
start "" "node_modules\electron\dist\electron.exe" .
exit /b 0

:no_folder
echo.
echo  [오류] electron_app_py 폴더를 찾을 수 없습니다.
echo  압축을 전부 푼 뒤, 풀린 폴더 안의 start.bat을 실행해 주세요.
goto :fail

:no_node
echo.
echo  [오류] Node.js가 설치되어 있지 않습니다.
echo  https://nodejs.org/ko 에서 LTS 버전을 설치한 뒤 다시 실행해 주세요.
goto :fail

:install_failed
echo.
echo  [오류] 실행 준비에 실패했습니다. 위의 메시지와 인터넷 연결을 확인해 주세요.
goto :fail

:fail
echo.
pause
exit /b 1
