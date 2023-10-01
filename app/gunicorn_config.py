import os

GUNICORN_WORKERS = int(os.environ.get("GUNICORN_WORKERS", "1"))
GUNICORN_THREADS = int(os.environ.get("GUNICORN_THREADS", "5"))


bind = ":8000"
workers = GUNICORN_WORKERS
threads = GUNICORN_THREADS

"""
Equivalent command
gunicorn --bind=:8000 --workers=1 --threads=5 app.main:app
"""
