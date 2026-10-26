# Piano di refactoring e riprogettazione — LiA

Stato: **piano Fase 1 + Fase 2 approvato per l'esecuzione autonoma; implementazione in corso** (vedi §8).

Branch di lavoro: `refactor/phase-1` (HEAD = `origin/main`, nessun commit locale; working tree intatto).

---

## 1. Situazione verificata

| Aspetto | Evidenza |
|---|---|
| Git | Nessun repository locale valido (la `.git` nella cartella padre è un guscio vuoto). Il remoto `Linked-IA` contiene solo `README.md` (3 commit). Repo inizializzato in `LinkedIA-main/` con `git reset` su `origin/main`: nessun file locale sovrascritto. |
| Archivio | Nessun `database/database.xlsx` presente. Esistono solo cache: `ohlcv_cache/*.pkl` (1,5 MB), `cache_embeddings/db_embeddings.pkl`, `cache_turbo/*.json`. |
| Ambiente Python | Python 3.14.4 di sistema, nessun venv (la `.venv` padre è vuota). Mancano pandas, flask, yfinance, pytest ecc. |
| Frontend | `node_modules` presenti ma corrotti (manca `vite/dist`, probabilmente escluso dalla regola `dist/` durante l'archiviazione): **la build di React e Vue fallisce** con `ERR_MODULE_NOT_FOUND`. |
| `.gitignore` | Non esclude `node_modules/`, `ohlcv_cache/`, `cache_*/`, `frontend-*/build`. |

Entry point reali: `main.py` (CLI interattiva, `input()`), `api_server.py` (Flask :5000), `start.py` (wrapper di `main.py`), `start-web.bat`, `main_filler.py` (`__main__`: riscrive l'archivio), `deepseek_manager.py` / `imf_validator.py` (`__main__`: chiamate a pagamento), `test_extra_addons.py` (script con rete e Perplexity, non un test).

### Flusso CLI (`main.py`)
data → RSS (3 feed) → se vuoto: Perplexity `selezione_intelligente` → `store_articles` (yfinance per 5 indici, `fill_dataframe` sull'**intero** archivio, DeepSeek `report_nesso`, scrittura Excel ×2) → rilettura Excel → `run_lia_deepseek` → `run_imf_validation`.

### Flusso API (`POST /api/analyze`)
Stessa raccolta, poi `store_articles` (che **già** chiama DeepSeek) → rilettura Excel → `run_analysis_deepseek` **di nuovo** → `run_lia_deepseek`. **Nessuna validazione IMF.** Le due pipeline divergono.

---

## 2. Problemi strutturali confermati

| ID | File:riga | Evidenza | Impatto | Intervento | Accettazione |
|---|---|---|---|---|---|
| S1 | `deepseek_manager.py:10`, `imf_validator.py:8` | Chiave DeepSeek incorporata (stesso valore nei due file) | Segreto esposto; va **revocata** dal proprietario | Config centralizzata, chiave da env, richiesta solo all'uso | `grep` di pattern chiave = 0; import senza env funzionante |
| S2 | `server.py` | `POST /exec` esegue `subprocess(..., shell=True)` arbitrario | Esecuzione remota di comandi | Rimozione (non referenziato dal codice; citato solo da doc obsolete) | File assente, doc riallineate |
| S3 | `api_server.py:279` | `app.run(debug=True, host='0.0.0.0')` | Debugger Werkzeug esposto in rete = RCE | Debug e host da config, default `127.0.0.1`, debug off | Test su `create_app()` |
| S4 | `api_server.py:171-177` | Risposta 500 con `trace` | Dettagli interni al client | Gestore errori centrale, messaggi utente, log lato server | Test: nessun `trace` nel JSON |
| S5 | `api_server.py:153` + `new_store_articles2.py:142` | DeepSeek eseguito due volte per richiesta API | Costo doppio, risultati non coerenti col DB | Pipeline unica condivisa CLI/API | Test con LLM finto: 1 chiamata per articolo |
| S6 | `main.py` vs `api_server.py` | Logica duplicata, IMF solo in CLI, feed RSS duplicati | Divergenza di comportamento | `pipeline.run_analysis()` usata da entrambi | Test di coerenza CLI/API |
| S7 | `deepseek_manager.py:36-39`, `LiA.py:90`, `analizer2.py:67` | Errore API restituito come testo e salvato come `report_nesso` | Errore mascherato da analisi valida, poi riusato nel pattern matching | Eccezione `ProviderUnavailable`, nessuna scrittura | Test: errore provider → nessun report salvato, risposta 502/503 |
| S8 | `archive_manager.py:106-111` | Errore Perplexity → `{"titolo": "Nessun evento"}` | Guasto indistinguibile da "nessuna notizia" | Eccezione distinta | Test |
| S9 | `fetcher.py:27`, `scraper.py:66` | Errori feed/scraping solo stampati | Feed rotto = "nessuna notizia" | Raccogliere esiti per fonte; fallimento totale ≠ vuoto | Test con feed finto in errore |
| S10 | `new_store_articles2.py:81` | Eccezione yfinance → prezzi `""` | Errore = dato mancante silenzioso; `""` mescolato a float | `None`/NaN esplicito + esito registrato | Test |
| S11 | `imf_validator.py:70-77` | `addons.get(..., 0) or 0` | Dato mancante trattato come 0 → "nessuno shock" | Mancante resta mancante; classificazione "dati insufficienti" | Test di caratterizzazione + test della correzione (separati) |
| S12 | tutti i provider | `requests.post` senza timeout (DeepSeek, Perplexity) | Richieste bloccate indefinitamente | Client HTTP condiviso: timeout, retry limitati solo su errori transitori | Test |
| S13 | `db_manager.py`, `new_store_articles2.py`, `deepseek_manager.py`, `imf_validator.py`, `api_server.py`, `main.py` | 9 punti leggono/scrivono l'Excel direttamente | Schema e conversioni dispersi | Modulo `storage/archive.py` unico | `grep read_excel` solo nel modulo |
| S14 | `extra_addons.py:19-20`, `main_filler.py:14,147` | Percorsi relativi alla cwd (`ohlcv_cache`, `database/database.xlsx`) | Comportamento diverso secondo la directory di avvio | Percorsi da config, base = radice progetto | Test con `tmp_path` |
| S15 | `extra_addons.py:35`, `main_filler.py:17` | `pickle.load` automatico delle cache | Esecuzione di codice da file non fidati | Cache in formato dati (CSV) caricate solo da percorso configurato; pkl esistenti ignorati e non cancellati | Nessun `pickle` nel package |
| S16 | `core_addons.py:5`, `db_manager.py:5`, `new_store_articles2.py:10`, `main_filler.py:35,43`, `extra_addons.py:278,384,453,730`, `fetcher.py:35,53`, `api_server.py:247` | Indici/ticker/calendari ridefiniti 11 volte | Incoerenza al primo cambiamento | `domain/markets.py` unico | `grep '\^GSPC'` = 1 occorrenza |
| S17 | ovunque | `print` diagnostici | Nessun livello, nessun log server | `logging` configurato in un punto; CLI conserva l'output utente | — |
| S18 | `LiA.py`, `analizer2.py` | Dichiarati DEPRECATI, non importati; richiedono `openai==0.28` | Dipendenze legacy (`openai`, `scikit-learn`) | Rimozione dopo commit di baseline (restano nella storia Git) | Import graph pulito |
| S19 | `requirements.txt` | `sentence-transformers`, `nltk`, `scikit-learn`, `openai==0.28`, `lxml` non usati dal flusso attivo | Installazione pesante, conflitti | Requisiti ridotti al codice attivo + extra `dev` | `pip install` + test in venv pulito |
| S20 | `main_filler.py:14`, `date_filter.py:5,58`, `extra_addons.py:96,663`, `fetcher.py:45`, `main.py:99` | Funzioni senza chiamanti (verificato con grep, nessun import dinamico) | Rumore | Rimozione | — |
| S21 | `main.py:99` | Funzione definita dopo `if __name__` | Codice morto | Rimozione | — |
| S22 | `setup.py` | Wizard OpenAI che chiede di modificare a mano i sorgenti; nome collide con setuptools | Fuorviante | Rimozione; configurazione via `.env.example` | — |
| S23 | `start.py:50-59` | Avvisa di chiavi in `archive_manager.py` (falso) | Diagnostica errata | Rimozione (sostituito da CLI) | — |
| S24 | `start-web.bat:22,28-31` | `pip install` a ogni avvio, `taskkill` su qualunque processo in :5000 | Effetti collaterali | Riscrittura minima o rimozione a favore di comandi documentati | — |
| S25 | `index.html`, `style.css` (radice) | UI statica "Terminale Web" scollegata dall'API | Terza interfaccia obsoleta | Rimozione | — |
| S26 | `frontend-react` / `frontend-vue` | Stesse 4 schermate e stessi endpoint; React più completo (302 righe AnalysisPage, recharts) e servito da Flask (`static_folder`) | Duplicazione | **Decisione rinviata al prompt Fase 2** (vedi §5) | Build del frontend attivo verde |
| S27 | 5 documenti + 2 report `.txt` | README locale descrive GPT/`LiA.py`; `LinkedIA_README.md` ≈ README remoto; report di sessione | Documentazione contraddittoria | README verificato, `docs/architecture.md`, report storici in `docs/history/` | Nessun riferimento a file inesistenti |
| S28 | `.gitignore` | Mancano `node_modules/`, cache, build | Rischio di commit di 125 MB e cache | Aggiornamento | `git status` pulito dopo build |
| S29 | `api_server.py:86,209` | Filtro `df['Data'] == date` dopo `read_excel` (tipo della colonna dipendente dal contenuto) | Possibili mancati match | Normalizzazione date nello storage | Test |
| S30 | `new_store_articles2.py:151` | Fallback `df["report_nesso"] = report_nesso_list` | Sovrascrittura dell'intera colonna se le lunghezze coincidono, eccezione altrimenti | Rimozione del ramo | Test |

---

## 3. Difetti metodologici (registrati, **non** corretti durante gli spostamenti)

Saranno corretti solo in task dedicati con test separato, oppure lasciati alla Fase 2 se toccano algoritmi previsionali.

| ID | Dove | Problema |
|---|---|---|
| M1 | `main_filler.py:88-91`, `deepseek_manager.py:80` | `momentum7` è **forward** (Close[T+7] − Close[T]): informazione futura salvata come indicatore e passata al LLM che "analizza" la notizia. Look-ahead. |
| M2 | `deepseek_manager.py:124-169` | Pattern storici cercati su **tutto** l'archivio, inclusi eventi successivi alla data analizzata e l'articolo stesso (appena salvato con il suo `report_nesso`). Nessun cutoff temporale. |
| M3 | `deepseek_manager.py:149-155,241-250` | Direzione = `SP500_Close > SP500_Close_prev` dello stesso giorno della notizia; "confidenza" = frequenza grezza su campioni di 2–10 casi, solo S&P 500, similarità per parole >4 caratteri in comune. |
| M4 | `new_store_articles2.py:56` | `get_last_trading_day` include il giorno della notizia: OHLCV dello stesso giorno senza sapere l'ora di pubblicazione. |
| M5 | `core_addons.py:41-81` via `main_filler.py:68` | `atr7`, `rv7`, `rs_vol7` calcolati su righe consecutive **dell'archivio articoli**, non su giorni di borsa; `idx` è un'etichetta usata con `iloc`. |
| M6 | `extra_addons.py:152-169` + `main_filler.py:79` | `drawdown` calcolato dal massimo della finestra di 15 giorni, descritto come "calo massimo dal picco". |
| M7 | `deepseek_manager.py:81` | `volatility7` descritta come "annualizzata"; è la deviazione standard giornaliera non annualizzata. |
| M8 | `extra_addons.py:242-659` | Fallback Perplexity che chiede a un LLM **prezzi storici** e li usa come dati di mercato. Valori potenzialmente inventati, indistinguibili da quelli di yfinance. |
| M9 | `imf_validator.py:11-57,106-129` | Valori e soglie presentati come "metriche IMF" senza riferimento a pubblicazioni specifiche; le soglie di `classifica_shock` sono arbitrarie ma etichettate come IMF. |
| M10 | `main.py:61` | Costo stimato fisso `0.0005 $` per articolo, non derivato dall'uso reale. |
| M11 | `main_filler.py:122-143` | Ogni salvataggio ricalcola tutto l'archivio e scarica T+7 per ogni riga e indice (rete, costi Perplexity). |

---

## 4. Decisioni dopo il prompt della Fase 2

Il prompt della Fase 2 chiede una nuova versione completa (backend, metodo, frontend React riprogettato, distribuzione online preparata). Le decisioni seguenti sostituiscono la struttura provvisoria.

| # | Problema | Scelta | Compromesso |
|---|---|---|---|
| D1 | Excel non regge job, stato, paginazione e riapertura identica | **SQLite (stdlib `sqlite3`)**, nessun ORM, nessun servizio esterno | Migrazione anticipata: autorizzata implicitamente dai requisiti di persistenza e job. Nessun archivio Excel esistente da importare (verificato). |
| D2 | La pipeline RSS→scraping→LLM produce testo libero non verificabile; i feed Reuters sono dismessi e i selettori CSS obsoleti | Evento = entità strutturata (data, orario e precisione, categoria, tag, fonti). Catalogo curato di eventi reali + creazione manuale protetta | RSS/scraping/Perplexity rimossi dal prodotto (restano nella storia Git). |
| D3 | Precedenti scelti con parole in comune su testi generati da LLM, senza cutoff (M2, M3) | Selezione deterministica: categoria + Jaccard sui tag, **solo eventi il cui esito all'orizzonte è osservabile entro il cutoff** | Meno "semantica", ma riproducibile e spiegabile. Embedding esclusi (non richiesti). |
| D4 | Indicatori con look-ahead e definizioni errate (M1, M4–M7) | Ricalcolo su sedute reali: input solo fino alla seduta base; esiti futuri in un blocco separato | Valori non confrontabili con l'archivio precedente (inesistente). |
| D5 | "Validazione IMF" con soglie non documentate (M9) | Rimossa | Nessuna classificazione di shock finché non c'è una fonte citabile. |
| D6 | Fallback prezzi via LLM (M8) | Rimosso: un prezzo mancante resta mancante e viene segnalato | Alcuni eventi possono avere copertura parziale. |
| D7 | `yfinance` pesante, scraping non documentato; Stooq protetto da verifica anti-bot | Provider `YahooChartProvider` con `requests` sull'endpoint chart (timeout, retry, validazione) | Endpoint non ufficiale: dipendenza esterna dichiarata, sostituibile via interfaccia. |
| D8 | IA chiamata a ogni richiesta | Sintesi IA **solo su richiesta esplicita**, con token di analista e chiave configurata; risultato strutturato JSON validato e persistito | Il caso dimostrativo può non avere sintesi: lo stato è mostrato. |
| D9 | Due frontend | **React** (indicato dal prompt). Vue rimosso. | — |
| D10 | Libreria grafica | **Recharts 3.10** (vedi §5) | SVG: oltre ~10k punti peggiora, ma i dati sono < 300 punti per serie. |
| D11 | Job | Esecutore in-process a un thread + stato in SQLite; i job interrotti dal riavvio vengono marcati come falliti | Nessuna coda esterna (YAGNI). Un solo processo applicativo in produzione. |
| D12 | Dipendenze | Backend: flask, requests, python-dotenv (+ gunicorn per il deploy). Niente pandas/numpy: i calcoli usano `statistics` | Codice numerico esplicito e testato. |

### Convenzione temporale (cuore del metodo)
- Ogni mercato ha fuso e orario di chiusura (`domain/markets.py`).
- **Seduta base (s=0)**: ultima seduta la cui chiusura è *anteriore* all'evento. Orario noto → confronto con la chiusura locale; orario sconosciuto → ultima seduta con data *precedente* alla data dell'evento (convenzione prudente, mostrata nell'interfaccia).
- s=+1 è la prima seduta che può riflettere l'evento; rendimenti e base 100 sono calcolati dalla chiusura di s=0.
- **Input al cutoff**: serie e indicatori fino a s=0. **Esiti**: sedute s>0, restituiti in un blocco separato e omessi in vista as-of.
- Un precedente entra nel campione per l'orizzonte h solo se la sua seduta s=h è anteriore alla seduta base dell'evento analizzato.

## 5. Libreria grafica

| Libreria | Serie temporali | Interazioni | Accessibilità | Licenza | Bundle (min+gz, indicativo) | Manutenzione |
|---|---|---|---|---|---|---|
| **Recharts** | buone (line, area, reference, brush) | tooltip, legenda, brush | SVG, `accessibilityLayer` da tastiera | MIT | ~100 kB | API dichiarativa React, già nel progetto |
| visx | ottime | da costruire | dipende dall'implementazione | MIT | modulare, piccolo | molto codice proprio |
| ECharts | ottime | ricche | canvas, aria generata | Apache-2.0 | ~300 kB+ | wrapper React non ufficiale |
| Plotly | ottime | ricche | limitata | MIT | ~1 MB | pesante |
| Lightweight Charts | eccellenti per prezzi | buone | canvas, limitata | Apache-2.0 + attribuzione | ~45 kB | non copre istogrammi/strip plot |

**Scelta: Recharts 3.10** (la 2.x è dichiarata non più mantenuta) — copre i quattro grafici con una sola libreria, è SVG e dichiarativa, licenza MIT. Ogni grafico ha comunque riepilogo testuale e tabella dati.

## 6. Prodotto

### Percorso principale
Home → "Apri il caso dimostrativo" → workspace (evento, mercato, grafico) → scheda Precedenti → scheda Esiti → Qualità/Fonti → Metodologia (link contestuali).

### Schermate
| Route | Contenuto |
|---|---|
| `/` | Valore, caso dimostrativo con anteprima reale, eventi disponibili, metodo in 3 passi, accesso alla creazione secondo i permessi |
| `/analysis/:id` | Workspace: intestazione evento, controlli (mercato, vista, finestra, orizzonte), schede Mercato / Precedenti / Esiti / Qualità e fonti / Sintesi IA |
| `/archive` | Ricerca, filtri (testo, categoria, stato, periodo), paginazione |
| `/methodology` | Definizioni con ancore richiamate dai grafici |
| `/new` | Creazione evento + analisi (solo con token analista) |

### Interazioni (V = solo visualizzazione, R = nuovo calcolo)
| Controllo | Effetto | Tipo |
|---|---|---|
| Mercato | serie, indicatori, precedenti e statistiche del mercato | V (dati già calcolati, nuova richiesta API in cache) |
| Vista retrospettiva/as-of | mostra/nasconde esiti futuri (backend omette il blocco) | V |
| Finestra ±10/20/60 | intervallo del grafico A | V |
| Orizzonte 1/5/20 | esiti e statistiche compatibili | V |
| Mostra/nascondi precedente | confronto B | V |
| Seleziona precedente | pannello dettagli con fonti | V |
| Nuova analisi | job di calcolo (gratuito) | R |
| Genera sintesi IA | job a pagamento, conferma esplicita | R |

Selezioni non sensibili nell'URL (`market`, `mode`, `window`, `h`, `tab`, `hide`, `sel`). Il token non va mai nell'URL.

### Contratti API (`/api`, JSON, errori `{error: {code, message}}`)
| Endpoint | Scopo |
|---|---|
| `GET /health` | stato |
| `GET /meta` | mercati, orizzonti, categorie, versione metodo, funzioni abilitate |
| `GET /featured` | id del caso dimostrativo |
| `GET /events` | elenco paginato con filtri e ultima analisi |
| `GET /events/:id` | evento e fonti |
| `POST /events` | crea evento e accoda analisi (token) → 202 |
| `GET /analyses` | archivio paginato (q, categoria, stato, periodo) |
| `GET /analyses/:id?market=&view=` | stato job, evento, risultato del mercato scelto |
| `POST /analyses/:id/summary` | accoda sintesi IA (token, conferma) → 202 |

### Dati per grafico
- **A**: `series[]` `{s, date, close, index100}` per s∈[-60,+60], `base` (data e close), `event` (timestamp, precisione, convenzione). Post-evento solo in `outcomes`.
- **B**: `precedents[].path[]` `{s, index100}` s∈[-20,+20], `target.path` per lo stesso intervallo.
- **C**: `stats[h]` `{n, returns[], median, q1, q3, min, max, up_count}` (+ esito evento in retrospettiva).
- **D**: `quality` `{sources, coverage, missing_sessions, usable_precedents[h], prices_updated_at, computed_at}`, `warnings[]`.

### Stati
Caricamento (scheletri), job in coda/in corso (polling, ripresa dopo ricarica), vuoto (nessun precedente, serie assente), parziale (orizzonte non ancora osservabile, dati mancanti), errore (messaggio + azione).

### Direzione visiva
Strumento editoriale-analitico: fondo carta chiaro / grafite in modalità scura, inchiostro quasi nero, un solo accento (petrolio), ambra per il marcatore dell'evento, blu/arancio per rialzi/ribassi (distinguibili da daltonici), numeri tabulari, griglia 8 px, angoli 6 px, ombre minime, animazioni ≤200 ms disattivate con `prefers-reduced-motion`.

## 7. Task (aggiornati)

| ID | Obiettivo | File/moduli | Tipo | Prio | Diff | Effort | Dip. | Accettazione | Verifiche |
|---|---|---|---|---|---|---|---|---|---|
| T01 | Baseline Git senza segreti, `.gitignore` | radice | config | P0 | D1 | low | — | nessuna chiave/cache/node_modules tracciati | `git ls-files`, grep |
| T02 | Rimozione codice obsoleto e pericoloso | legacy, `server.py`, Vue, UI statica | pulizia | P0 | D1 | low | T01 | nessun riferimento residuo | grep |
| T03 | Ambiente: `pyproject.toml`, venv, requisiti | radice | config | P0 | D2 | medium | T01 | install pulito | pip + pytest |
| T04 | Config, errori, logging | `linkedia/config.py`, `errors.py` | refactor | P0 | D2 | medium | T03 | import senza chiavi | test |
| T05 | Dominio: mercati, sedute, indicatori, statistiche | `linkedia/domain/*` | nuovo | P0 | D5 | max | T04 | convenzione temporale testata, nessun look-ahead | test |
| T06 | Selezione precedenti con cutoff | `domain/precedents.py` | nuovo | P0 | D5 | max | T05 | nessun precedente con esito oltre il cutoff | test |
| T07 | Provider prezzi e LLM | `linkedia/providers/*` | nuovo | P1 | D3 | high | T04 | errori distinti, timeout, validazione | test con transport finto |
| T08 | Storage SQLite + catalogo eventi | `linkedia/storage/*`, `data/events.json` | nuovo | P0 | D3 | high | T05 | riapertura identica | test |
| T09 | Servizio analisi + job | `linkedia/services/*` | nuovo | P0 | D4 | xhigh | T06–T08 | CLI e API usano lo stesso servizio | test |
| T10 | API e CLI | `linkedia/api`, `linkedia/cli.py` | nuovo | P0 | D3 | high | T09 | contratti §6 | test client |
| T11 | Seed reale e verifica end-to-end | CLI | verifica | P0 | D4 | xhigh | T10 | caso reale aperto da API | curl |
| T12 | Frontend: fondamenta (token, layout, routing, API client) | `frontend/` | nuovo | P0 | D3 | high | T10 | build verde | build |
| T13 | Workspace e grafici A–D | `frontend/src/features/analysis` | nuovo | P0 | D4 | xhigh | T12 | valori = API | test + browser |
| T14 | Home, archivio, metodologia, creazione | `frontend/src/pages` | nuovo | P1 | D3 | high | T13 | flussi completi | browser |
| T15 | Accessibilità e responsive | frontend | verifica | P1 | D3 | high | T14 | tastiera, focus, mobile | browser |
| T16 | CI, Dockerfile, documentazione | radice, `docs/` | config/doc | P1 | D2 | medium | T15 | CI offline, README verificato | esecuzione locale |

Ordine reale: T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11 → T12 → T13 → T14 → T15 → T16.

## 8. Avanzamento
- [x] Esplorazione e diagnosi
- [x] Piano Fase 1 + Fase 2
- [ ] Implementazione (vedi task)
