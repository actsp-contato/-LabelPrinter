@echo off
title LabelPrinter ACT - Elgin i9
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
start "" http://127.0.0.1:5000
waitress-serve --listen=0.0.0.0:5000 wsgi:app
pause
