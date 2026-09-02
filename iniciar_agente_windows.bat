@echo off
title Agente de Impressao - LabelPrinter ACT
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
set /p LABELPRINTER_URL=URL do LabelPrinter no Render: 
set /p PRINT_AGENT_TOKEN=Token do agente de impressao: 
set /p PRINTER_NAME=Nome da impressora local (Enter para padrao): 
python print_agent.py
pause
