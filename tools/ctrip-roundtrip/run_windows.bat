@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo Ctrip Round Trip: TAO - MEL
echo 2027-02-01 Qingdao to Melbourne
echo 2027-02-14 Melbourne to Qingdao
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found.
  echo Please install Python 3.11 first.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 py -m venv .venv
)

echo [2/3] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo.
echo [3/3] Starting Ctrip round-trip search...
echo.
".venv\Scripts\python.exe" ctrip_roundtrip_qingdao_melbourne.py

echo.
pause
