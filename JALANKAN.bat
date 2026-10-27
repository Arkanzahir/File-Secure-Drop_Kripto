@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 server.py --open
  goto selesai
)
where python >nul 2>nul
if %errorlevel% equ 0 (
  python server.py --open
  goto selesai
)
echo Python 3 belum ditemukan. Pasang Python 3.10 atau lebih baru.
:selesai
pause
