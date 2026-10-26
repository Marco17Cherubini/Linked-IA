# Immagine di produzione: frontend compilato servito da Flask/Gunicorn.

FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LIA_DATABASE_PATH=/data/lia.sqlite3
WORKDIR /app
COPY pyproject.toml README.md ./
COPY linkedia/ linkedia/
RUN pip install --no-cache-dir ".[deploy]" \
    && useradd --create-home lia \
    && mkdir -p /data && chown lia /data
COPY --from=frontend /app/frontend/dist frontend/dist
USER lia
VOLUME ["/data"]
EXPOSE 8000
# Un solo processo: i job in background vivono nel processo e il loro stato in SQLite.
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--bind", "0.0.0.0:8000", "linkedia.wsgi:app"]
