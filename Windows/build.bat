@echo off
setlocal

:: Find Python (try python, then py, then common install paths)
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if not defined PYTHON (
    where py >nul 2>&1 && set PYTHON=py
)
if not defined PYTHON (
    for /d %%i in ("%LOCALAPPDATA%\Programs\Python\Python3*") do set PYTHON=%%i\python.exe
)
if not defined PYTHON (
    echo [ERROR] Python not found.
    echo Please install Python from https://www.python.org/downloads/
    echo During installation: check "Add Python to PATH"
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
echo.

echo Installing dependencies...
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Building EXE...
%PYTHON% -m PyInstaller --onefile --name sm2_tool sm2_tool.py
if errorlevel 1 goto error

echo.
echo Done! EXE: dist\sm2_tool.exe
pause
exit /b 0

:error
echo.
echo [ERROR] Build failed. See output above.
pause
exit /b 1
