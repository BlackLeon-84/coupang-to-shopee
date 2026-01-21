@echo off
chcp 65001 > nul
setlocal

:: ==========================================
:: [쿠팡 -> 쇼피] 자동 소싱 프로그램
:: ==========================================

:: 프로그램 폴더로 이동
cd /d "%~dp0"

:: 실행
:: 1. 필수 패키지 확인 (조용히)
pip install -r requirements.txt > nul 2>&1

:: 2. 프로그램 실행 (터미널 숨김 모드)
start pythonw gui_app.py

endlocal
