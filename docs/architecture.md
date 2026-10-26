# Architettura

## Visione d'insieme

```
browser (React)  ──HTTP JSON──▶  linkedia.api (Flask)  ──▶  linkedia.services  ──▶  linkedia.domain (puro)
                                         ▲                       │      │
linkedia.cli ────────────────────────────┘                       │      └──▶ linkedia.storage (SQLite)
                                                                 └──▶ linkedia.providers (Yahoo, DeepSeek)
```

CLI e API usano gli stessi servizi: non esiste una seconda pipeline.

## Moduli e responsabilità

| Modulo | Responsabilità | Può importare |
|---|---|---|
| `linkedia/config.py` | lettura e validazione delle variabili d'ambiente, percorsi assoluti | `errors` |
| `linkedia/errors.py` | errori con codice stabile e messaggio per l'utente | — |
| `linkedia/domain/markets.py` | indici, simboli, fusi, orari di chiusura | — |
| `linkedia/domain/events.py` | modello e validazione degli eventi e delle fonti | — |
| `linkedia/domain/sessions.py` | sedute utilizzabili, convenzione evento → seduta base | `domain` |
| `linkedia/domain/indicators.py` | indicatori al cutoff, rendimenti futuri | `domain` |
| `linkedia/domain/precedents.py` | pertinenza e punteggio dei precedenti | `domain` |
| `linkedia/domain/sample_stats.py` | statistiche descrittive con numerosità minime | — |
| `linkedia/domain/analysis.py` | risultato evento × mercato serializzabile | `domain` |
| `linkedia/providers/http.py` | timeout, retry limitati, TLS con certificati di sistema | `errors` |
| `linkedia/providers/market_data.py` | prezzi giornalieri (Yahoo chart API), validazione | `domain`, `errors` |
| `linkedia/providers/llm.py` | client DeepSeek (JSON mode) | `errors` |
| `linkedia/storage/store.py` | SQLite: eventi, fonti, prezzi, analisi, sintesi | `domain`, `errors` |
| `linkedia/services/analysis.py` | creazione eventi, sincronizzazione prezzi, calcolo analisi | tutto tranne `api`/`cli` |
| `linkedia/services/summary.py` | sintesi IA: permessi, limiti, prompt, validazione | idem |
| `linkedia/services/jobs.py` | esecutore in background (1 thread) o in linea | — |
| `linkedia/api/` | rotte JSON, gestione errori, intestazioni di sicurezza, frontend statico | `services`, `storage`, `domain` |
| `linkedia/cli.py` | `seed`, `analyze`, `events`, `serve` | `services`, `storage` |

Importare un modulo non apre connessioni, non legge chiavi e non scrive file: `Settings.from_env()` e `create_app()` sono chiamati esplicitamente.

## Metodo (versione 2.0.0)

1. **Seduta base (s = 0)** per ciascun mercato: ultima seduta chiusa prima dell'evento. Orario noto → confronto con la chiusura locale (fuso del mercato, orario per data); orario sconosciuto → ultima seduta con data precedente alla data dell'evento.
2. **Input al cutoff** (`observed`): serie fino a s = 0 e indicatori (`ret_1`, `ret_5`, `vol_20` annualizzata, `drawdown_60`, `zscore_20`, `range_1`).
3. **Esiti** (`outcomes`): serie s > 0, rendimenti a 1/5/20 sedute, minimo nelle 20 sedute successive.
4. **Precedenti**: stessa categoria o ≥ 2 etichette comuni; punteggio 0,6 × categoria + 0,4 × Jaccard; massimo 6; ammessi solo se la loro seduta +20 è ≤ seduta base dell'evento analizzato.
5. **Statistiche**: n, valori, min/max; mediana con n ≥ 3; quartili con n ≥ 5; conteggio dei rialzi come frequenza osservata.

Ogni risultato è salvato come JSON immutabile con la versione del metodo e un'istantanea dell'evento.

## Persistenza

SQLite (`instance/lia.sqlite3`, configurabile). Tabelle: `events`, `sources`, `prices`, `price_sync`, `analyses`, `summaries`, `meta`. Lo stato dei job (`queued`, `running`, `succeeded`, `failed`) è nel database; all'avvio i job rimasti aperti vengono marcati `interrupted`.

I prezzi si scaricano una volta per mercato per l'intervallo del catalogo e si aggiornano al più una volta al giorno; dopo un errore del provider si attende 10 minuti prima di riprovare.

## Contratti API

Tutte le risposte sono JSON. Errori: `{"error": {"code", "message"}}` con stato HTTP coerente (400 input non valido, 403 permessi, 404 non trovato, 409 conflitto, 502 provider non disponibile, 503 funzione non configurata, 500 errore interno senza dettagli).

| Metodo e percorso | Descrizione |
|---|---|
| `GET /api/health` | stato e versione |
| `GET /api/meta` | mercati, orizzonti, categorie, criteri dei precedenti, funzioni abilitate |
| `GET /api/featured` | `{event_id, analysis_id}` del caso dimostrativo |
| `GET /api/events?q&category&page&page_size` | eventi con l'analisi da mostrare (ultima completata) |
| `GET /api/events/:id` | evento e fonti |
| `POST /api/events` | crea evento e accoda l'analisi (token) → 202 `{event_id, analysis_id}` |
| `POST /api/events/:id/analyses` | ricalcola (token) → 202 |
| `GET /api/analyses?q&category&status&from&to&page&page_size` | archivio paginato (max 50 per pagina) |
| `GET /api/analyses/:id?market&view` | stato, evento, mercati disponibili, risultato del mercato scelto; `view=as_of` omette `outcomes`; ETag |
| `POST /api/analyses/:id/summary` | `{confirm_cost: true, regenerate?}` (token) → 202 |

Forma di `data` (un mercato):

```
market, status, warnings[{code, severity, message}],
base {date, close, close_at, rule, rule_description}, event_time {occurred_on, occurred_at, precision},
observed {series[{s, date, close, index100}], indicators[{id, label, value, unit, window, description, reason}]},
outcomes {series[...], returns[{h, value, end_date}], min_after {h, value}},      # solo vista retrospettiva
first_reaction {date}, target_path[{s, index100}],
precedents {criteria, cutoff_date, items[{event_id, title, occurred_on, score, shared_tags, base_date,
            returns{1,5,20}, min_after, path[{s, index100}], sources[]}], eligible_count, excluded{}},
stats {"1"|"5"|"20": {n, values[], median, q1, q3, min, max, up_count, observed_up_frequency, small_sample, notes[]}},
quality {sessions_available, coverage{first_date, last_date}, window{start, end, sessions},
         missing_in_window, pre_event_sessions, usable_precedents{}}
```

Unità: rendimenti e indicatori in punti percentuali (1.5 = +1,5 %), `vol_20` in % annua, `zscore_20` in deviazioni standard. Date `YYYY-MM-DD` di calendario del mercato; istanti ISO 8601 con offset.

## Frontend

React 18 + Vite + React Router + Recharts 3. Le selezioni di visualizzazione (`market`, `view`, `win`, `h`, `tab`, `hide`, `sel`) stanno nell'URL. Il cambio di mercato o vista richiede una nuova risposta all'API (già calcolata, in cache); finestra, orizzonte, precedenti visibili e schede sono solo visualizzazione. Nessuna interazione ordinaria avvia chiamate IA.

| Cartella | Contenuto |
|---|---|
| `src/features/analysis/` | workspace, grafici A–C, pannelli, polling dei job |
| `src/pages/` | home, archivio, metodologia, creazione |
| `src/components/` | layout, controlli, schede, stati, definizioni (`InfoTip`) |
| `src/content/glossary.js` | definizioni condivise tra grafici e Metodologia |
| `src/styles/` | token (chiaro/scuro), base, componenti, pagine |

## Sicurezza

- Nessun segreto nei sorgenti; la chiave DeepSeek storica va revocata (vedi piano).
- Token analista confrontato a tempo costante; mai nell'URL; nel browser solo in `sessionStorage`.
- Debug disattivato di default, host `127.0.0.1` per il server di sviluppo, CSP restrittiva, limite di 64 kB per le richieste.
- TLS verificato con l'archivio certificati del sistema operativo (`truststore`).
