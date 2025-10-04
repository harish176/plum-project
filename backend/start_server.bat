@echo off
cd /d C:\Users\nhari\siddu\backend
python -m uvicorn main:app --reload --host localhost --port 8000
pause