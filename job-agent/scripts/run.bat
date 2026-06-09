@echo off
REM 일일 실행 진입점 (작업 스케줄러가 이 파일을 호출)
cd /d "%~dp0.."
if not exist "..\data" mkdir "..\data"
python -m jobagent.main >> "..\data\run.log" 2>&1
