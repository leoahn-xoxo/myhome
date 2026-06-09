@echo off
REM 최초 1회: 각 구직 사이트에 로그인해 세션을 전용 프로필에 저장
cd /d "%~dp0.."
python -m jobagent.main --login
pause
