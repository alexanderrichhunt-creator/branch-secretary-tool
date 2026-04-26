@echo off
setlocal

cd /d "%~dp0"

echo.
echo Branch Secretary Tool - starter
echo.

echo [1/4] Checking virtual environment...
REM Create venv if missing
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 goto error
)

echo [2/4] Activating environment...
REM Activate venv
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

echo [3/4] Installing dependencies...
REM Install dependencies
echo Installing dependencies (this may take a minute the first time)...
python -m pip install --upgrade pip
if errorlevel 1 goto error
pip install -r requirements.txt
if errorlevel 1 goto error

echo [4/4] Ensuring .env exists...
REM Create .env from example if missing
if not exist ".env" (
  echo Creating .env from .env.example...
  copy /y ".env.example" ".env" >nul
)

REM Open browser (best-effort) and run the app
echo.
echo Starting the app...
echo Open: http://127.0.0.1:5000
echo.

start "" "http://127.0.0.1:5000"
if /I "%~1"=="--new-window" (
  echo Opening server in a new window...
  start "Branch Secretary Tool" cmd /k ""%~dp0.venv\Scripts\activate.bat" ^& python "%~dp0run.py""
) else (
  echo Running server in this window - recommended in Cursor...
  python run.py
)
goto :eof

:error
echo.
echo ERROR: Something went wrong while starting the app.
echo If you see "python is not recognized", install Python from python.org and check "Add to PATH".
echo.
pause
exit /b 1

