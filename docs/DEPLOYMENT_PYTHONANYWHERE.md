# PythonAnywhere Deployment Guide

This project is ready to run on PythonAnywhere as a normal Django web app.

## 1. Upload the project

- Upload the repo to your PythonAnywhere home directory.
- Create a virtualenv for the site, for example:

```bash
python -m venv ~/.virtualenvs/realstateproject
source ~/.virtualenvs/realstateproject/bin/activate
pip install -r /home/yourusername/RealStateproject/requirements.txt
```

## 2. Configure environment variables

Set these in the PythonAnywhere `Web` tab or in your shell:

- `DJANGO_SETTINGS_MODULE=realstateproject.settings`
- `DJANGO_SECRET_KEY=<strong-random-secret>`
- `DEBUG=False`
- `ALLOWED_HOSTS=<yourusername>.pythonanywhere.com`
- `CSRF_TRUSTED_ORIGINS=https://<yourusername>.pythonanywhere.com`
- `BASE_URL=https://<yourusername>.pythonanywhere.com`

If you use MySQL:

- `DB_ENGINE=mysql`
- `MYSQL_NAME=<database_name>`
- `MYSQL_USER=<database_user>`
- `MYSQL_PASSWORD=<database_password>`
- `MYSQL_HOST=<mysql_host>`
- `MYSQL_PORT=3306`

If you want the fastest first live deploy, you can keep SQLite for now by not setting the MySQL variables.

## 3. WSGI configuration

Point the PythonAnywhere WSGI file to:

```python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "realstateproject.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

The repo now includes matching WSGI entry points in:

- `realstateproject/wsgi.py`
- `wsgi.py`

## 4. Static files

Run:

```bash
python manage.py collectstatic --noinput
```

Then configure PythonAnywhere static mapping:

- URL: `/static/`
- Directory: `/home/yourusername/RealStateproject/staticfiles`

If you serve media uploads on PythonAnywhere, map:

- URL: `/media/`
- Directory: `/home/yourusername/RealStateproject/media`

## 5. Database

If you use SQLite for the first live launch:

- No extra database setup is needed.

If you use MySQL:

- Create a MySQL database in PythonAnywhere.
- Run migrations after setting DB env vars:

```bash
python manage.py migrate
```

## 6. Final checks

Run these inside the virtualenv:

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
```

## 7. Notes

- The dashboard and wallet pages now cache repeated renders briefly, which helps on a shared host.
- Channels/real-time features fall back to in-memory layers when Redis is not available.
- If you later want WebSockets or background workers, configure Redis/Celery separately.
