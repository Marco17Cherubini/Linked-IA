# LiA — Linked Intelligent Analyst

LiA collega un evento documentato (guerra, decisione di banca centrale, crisi bancaria, elezione…) ai movimenti di cinque indici azionari — S&P 500, Nasdaq Composite, DAX 40, FTSE 100, Nikkei 225 — e lo confronta con precedenti storici scelti con regole esplicite.

Per ogni analisi mostra:

- **evento e fonti**, con data, orario, fuso e precisione dichiarata;
- **mercato intorno all'evento** in base 100 o in livello, con la seduta base e la distinzione prima/dopo;
- **precedenti** il cui esito era già osservabile alla data dell'evento, con serie confrontabili e fonti;
- **esiti del campione** (singoli casi o istogramma), con numerosità, mediana e quartili solo quando calcolabili;
- **qualità e copertura** dei dati, avvisi e convenzioni applicate;
- una **sintesi IA facoltativa**, generata solo su richiesta esplicita di un analista.

LiA descrive casi storici: non fornisce previsioni, probabilità o consigli di investimento. I metodi sono descritti in [docs/architecture.md](docs/architecture.md) e nella pagina *Metodologia* dell'applicazione.

## Avvio rapido

Prerequisiti: Python ≥ 3.11 e Node ≥ 20. Sequenza verificata su Windows 11 con Python 3.14 e Node 24 (le dipendenze del frontend sono state installate con `npm install` sullo stesso `package-lock.json`).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # su Linux/macOS: .venv/bin/python
cd frontend && npm ci && npm run build && cd ..
.venv/Scripts/python -m linkedia seed               # scarica i prezzi (gratis) e calcola il catalogo
.venv/Scripts/python -m linkedia serve              # http://127.0.0.1:5000
```

`seed` importa i 34 eventi del catalogo curato (`linkedia/data/events.json`), scarica i prezzi giornalieri dei cinque indici dall'endpoint pubblico di Yahoo Finance e salva le analisi in `instance/lia.sqlite3`. Nessun comando chiama servizi a pagamento.

Per lo sviluppo del frontend con ricaricamento automatico: `npm run dev` in `frontend/` (porta 5173, inoltra `/api` a Flask sulla 5000).

## Configurazione

Copiare `.env.example` in `.env`. Senza alcuna variabile l'applicazione funziona in sola consultazione.

| Variabile | Effetto |
|---|---|
| `LIA_ADMIN_TOKEN` | abilita la creazione di analisi e la richiesta di sintesi IA per chi presenta il token |
| `DEEPSEEK_API_KEY` | abilita la sintesi IA (servizio a pagamento), insieme al token |
| `LIA_DATABASE_PATH` | percorso del database SQLite (default `instance/lia.sqlite3`) |

L'elenco completo è in `.env.example`.

## Verifiche

```bash
.venv/Scripts/python -m pytest          # test offline: la rete è bloccata, nessuna chiave richiesta
.venv/Scripts/ruff check .
cd frontend && npm test && npm run build
.venv/Scripts/python -m pytest -m external   # facoltativo: interroga davvero il provider prezzi
```

La CI (`.github/workflows/ci.yml`) esegue lint, test e build; lo smoke test esterno parte solo manualmente.

## Distribuzione

Il `Dockerfile` compila il frontend e avvia Gunicorn con un solo processo (i job in background vivono nel processo, il loro stato in SQLite):

```bash
docker build -t lia .
docker run -p 8000:8000 -v lia-data:/data --env-file .env lia
docker run --rm -v lia-data:/data lia python -m linkedia seed
```

Il volume `/data` deve essere persistente. Su un host pubblico impostare un `LIA_ADMIN_TOKEN` robusto e servire l'applicazione dietro HTTPS. Il Dockerfile non è stato eseguito in questo ambiente (Docker non installato).

## Struttura

```
linkedia/            backend Python (dominio, provider, storage, servizi, API Flask, CLI)
frontend/            React + Vite + Recharts
tests/               test pytest offline
docs/                architettura, decisioni, piano, documenti storici
```

## Limiti noti

- Il catalogo è piccolo e curato: i campioni di precedenti contano pochi casi e lo dichiarano.
- I prezzi provengono da un endpoint pubblico non ufficiale; lacune ed errori vengono segnalati, non sostituiti.
- Le fonti del catalogo sono voci di Wikipedia e comunicati ufficiali, non notizie originali dell'epoca.

Progetto accademico — Università del Piemonte Orientale. La versione precedente della pipeline è documentata in [docs/history/](docs/history/).
