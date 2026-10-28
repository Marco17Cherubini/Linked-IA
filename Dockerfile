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
    && useradd --create-home --uid 10001 lia \
    && mkdir -p /data && chown lia /data
COPY --from=frontend /app/frontend/dist frontend/dist
COPY docker-entrypoint.sh /usr/local/bin/lia-start
RUN chmod 755 /usr/local/bin/lia-start
EXPOSE 8000
# Parte come root solo per sistemare i permessi del volume, poi passa all'utente `lia`.
CMD ["/usr/local/bin/lia-start"]
