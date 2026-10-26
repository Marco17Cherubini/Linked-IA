"""Entry point WSGI per la produzione: `gunicorn linkedia.wsgi:app`."""

from .api import create_app

app = create_app()
