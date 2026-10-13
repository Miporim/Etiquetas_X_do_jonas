@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name EtiquetasJonas --distpath entrega\EtiquetasJonas --workpath build main.py
if errorlevel 1 pause
