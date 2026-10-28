#!/bin/sh
# Avvio in produzione. I volumi di Railway sono montati come root: si sistemano i permessi della
# directory dei dati e poi si continua come utente senza privilegi.
set -eu

DATA_DIR="$(dirname "${LIA_DATABASE_PATH:-/data/lia.sqlite3}")"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    chown -R lia:lia "$DATA_DIR"
    export HOME=/home/lia
    exec setpriv --reuid=lia --regid=lia --init-groups "$0" "$@"
fi

# Schema, catalogo e analisi dimostrative mancanti: idempotente, non cancella nulla e non usa
# servizi a pagamento. Un errore del provider prezzi non impedisce l'avvio del sito.
python -m linkedia init || echo "init: alcune analisi dimostrative non sono state calcolate (vedi log)"

# Un solo processo: i job in background vivono nel processo e il loro stato in SQLite.
# Nessun access log applicativo: i log HTTP sono già raccolti dalla piattaforma.
exec gunicorn --workers 1 --threads 8 --bind "0.0.0.0:${PORT:-8000}" \
    --timeout 60 --graceful-timeout 20 linkedia.wsgi:app
