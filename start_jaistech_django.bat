@echo off
echo ================================
echo Starting Django Server...
echo ================================
cd /d "%~dp0"
start cmd /k "python manage.py runserver 8080"
timeout /t 3 > nul
start chrome http://localhost:8080
