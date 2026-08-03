@echo off
cd /d "%~dp0\.."
echo Starting UBT Farm Web Server on port 5001...
start http://localhost:5001/
./venv/Scripts/python.exe web_app/app.py --port 5001
pause
