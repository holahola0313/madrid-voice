@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing project environment. See RUN_LOCAL.md to install dependencies.
  pause
  exit /b 1
)
echo Madrid Voice - local personal project
echo Open http://127.0.0.1:8501 in your browser.
echo Keep this window open. Press Ctrl+C to stop the dashboard.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless false --browser.gatherUsageStats false
pause
