@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo  ==========================================
echo   FurryArt AI - Starting...
echo  ==========================================
echo.

REM --- Find Python ---
set PYTHON=

REM 1. Non-standard path (Python 3.15 on this PC)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set PYTHON=%LOCALAPPDATA%\Python\bin\python.exe
    goto :found_py
)

REM 2. Standard Windows paths
if exist "%LOCALAPPDATA%\Programs\Python\Python315\python.exe" (
    set PYTHON=%LOCALAPPDATA%\Programs\Python\Python315\python.exe
    goto :found_py
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
    goto :found_py
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
    goto :found_py
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
    goto :found_py
)
if exist "C:\Python312\python.exe" (
    set PYTHON=C:\Python312\python.exe
    goto :found_py
)

REM 3. Try python from PATH
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :found_py
)

REM 4. Try py launcher
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :found_py
)

echo  ERROR: Python not found!
echo  Please install Python from https://www.python.org/downloads/
pause
exit /b 1

:found_py
echo  Python found: %PYTHON%
echo.

REM --- Check .env file ---
if not exist ".env" (
    echo  WARNING: .env file not found!
    echo  Please add your Gemini API key to .env
    echo  Get key: https://aistudio.google.com/apikey
    echo.
    if exist ".env.example" copy ".env.example" ".env" >nul
    notepad .env
    echo  After saving .env press Enter...
    pause >nul
)

REM --- Install dependencies ---
echo  Installing/checking dependencies...
"%PYTHON%" -m pip install flask google-generativeai pillow python-dotenv requests --quiet
if errorlevel 1 (
    echo  ERROR! Try running as Administrator.
    pause
    exit /b 1
)

echo  Done!
echo.
echo  ==========================================
echo   Open browser: http://localhost:5000
echo  ==========================================
echo.
start http://localhost:5000
"%PYTHON%" app.py
pause
exit /b 0
