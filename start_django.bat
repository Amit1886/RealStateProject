@echo off
echo Starting Django server...
start cmd /k "python manage.py runserver 8080"
timeout /t 3 > nul
start chrome http://localhost:8080
