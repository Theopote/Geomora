@echo off
cd /d %~dp0backend
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\uvicorn geomora_rectify.server:app --host 127.0.0.1 --port 8765
