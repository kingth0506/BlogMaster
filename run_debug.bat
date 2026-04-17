@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python main.py 2>&1
echo.
echo === 위에 에러가 있으면 스크린샷 찍어주세요 ===
pause
