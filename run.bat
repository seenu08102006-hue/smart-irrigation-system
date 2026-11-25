@echo off
REM One-click launcher (Windows): sets up everything on first run, then starts the app.
cd /d "%~dp0"

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  call .venv\Scripts\activate
  pip install -r backend\requirements.txt
) else (
  call .venv\Scripts\activate
)

if not exist backend\static\index.html (
  echo Building frontend...
  pushd frontend
  call npm install
  call npm run build
  popd
)

echo Open http://localhost:5000
python backend\app.py
