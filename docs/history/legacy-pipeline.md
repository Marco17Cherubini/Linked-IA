# LinkedIA — Linked Intelligent Analyst

**Dove notizie e mercati si incontrano**

LinkedIA è un prototipo sperimentale di intelligenza artificiale che analizza notizie finanziarie e geopolitiche, le collega ai dati storici di mercato (OHLCV + indicatori) e genera previsioni basate su pattern matching e validazione con metriche del Fondo Monetario Internazionale.

Progetto accademico — Università del Piemonte Orientale (UNIUPO).

---

## Indice

1. [Panoramica del Sistema](#1-panoramica-del-sistema)
2. [Albero delle Dipendenze](#2-albero-delle-dipendenze)
3. [Flusso di Esecuzione](#3-flusso-di-esecuzione)
4. [Descrizione dei Moduli](#4-descrizione-dei-moduli)
   - 4.1 [main.py — Entry Point](#41-mainpy--entry-point)
   - 4.2 [fetcher.py — Raccolta Notizie RSS](#42-fetcherpy--raccolta-notizie-rss)
   - 4.3 [scraper.py — Web Scraping Articoli](#43-scraperpy--web-scraping-articoli)
   - 4.4 [archive_manager.py — Selezione Intelligente (Perplexity)](#44-archive_managerpy--selezione-intelligente-perplexity)
   - 4.5 [new_store_articles2.py — Elaborazione e Salvataggio Articoli](#45-new_store_articles2py--elaborazione-e-salvataggio-articoli)
   - 4.6 [db_manager.py — Gestione Database Excel](#46-db_managerpy--gestione-database-excel)
   - 4.7 [date_filter.py — Calendari di Mercato e Trading Days](#47-date_filterpy--calendari-di-mercato-e-trading-days)
   - 4.8 [close_prev.py — Prezzo di Chiusura Precedente](#48-close_prevpy--prezzo-di-chiusura-precedente)
   - 4.9 [main_filler.py — Orchestratore Riempimento Dati](#49-main_fillerpy--orchestratore-riempimento-dati)
   - 4.10 [core_addons.py — Indicatori Finanziari Base](#410-core_addonspy--indicatori-finanziari-base)
   - 4.11 [extra_addons.py — Indicatori Finanziari Avanzati](#411-extra_addonspy--indicatori-finanziari-avanzati)
   - 4.12 [deepseek_manager.py — Analisi Pattern con DeepSeek AI](#412-deepseek_managerpy--analisi-pattern-con-deepseek-ai)
   - 4.13 [imf_validator.py — Validazione con Metriche IMF](#413-imf_validatorpy--validazione-con-metriche-imf)
5. [Schema del Database](#5-schema-del-database)
6. [Add-ons Finanziari](#6-add-ons-finanziari)
7. [API e Modelli AI Utilizzati](#7-api-e-modelli-ai-utilizzati)
8. [Installazione e Avvio](#8-installazione-e-avvio)
9. [Limitazioni e Sviluppi Futuri](#9-limitazioni-e-sviluppi-futuri)

---

## 1. Panoramica del Sistema

LinkedIA è un sistema a pipeline che opera in cinque macro-fasi:

| Fase | Descrizione | Moduli coinvolti |
|------|-------------|------------------|
| **1. Raccolta Notizie** | Recupero articoli da feed RSS oppure, in assenza, ricerca intelligente via Perplexity AI | `fetcher.py`, `scraper.py`, `archive_manager.py` |
| **2. Dati di Mercato** | Download prezzi OHLCV da Yahoo Finance per 5 indici globali, calcolo Close_prev e individuazione del trading day corretto | `new_store_articles2.py`, `close_prev.py`, `date_filter.py` |
| **3. Calcolo Indicatori** | Calcolo di 14 indicatori finanziari (7 core + 7 extra) per ciascuno dei 5 indici | `main_filler.py`, `core_addons.py`, `extra_addons.py` |
| **4. Analisi Semantica-Numerica** | Generazione del `report_nesso` per ogni articolo (collegamento notizia ↔ dati di mercato) e pattern matching storico con DeepSeek AI | `deepseek_manager.py` |
| **5. Validazione IMF** | Controllo incrociato dei risultati con le metriche di riferimento del Fondo Monetario Internazionale, classificazione dello shock e previsione della durata degli effetti | `imf_validator.py` |

**Indici monitorati:** S&P 500, NASDAQ Composite, DAX 40, FTSE 100, Nikkei 225.

---

## 2. Albero delle Dipendenze

Di seguito la mappa completa dei moduli richiamati a partire da `main.py`. Solo questi 13 file partecipano attivamente all'esecuzione del programma.

```
main.py                              ← entry point
├── fetcher.py                       ← raccolta RSS (foglia)
├── scraper.py                       ← web scraping (foglia)
├── archive_manager.py               ← selezione intelligente Perplexity (foglia)
├── new_store_articles2.py           ← elaborazione e salvataggio
│   ├── main_filler.py               ← orchestratore riempimento
│   │   ├── core_addons.py           ← indicatori base (foglia)
│   │   ├── extra_addons.py          ← indicatori avanzati (foglia)
│   │   └── close_prev.py            ← close precedente (foglia)
│   ├── close_prev.py                ← (già elencato)
│   ├── db_manager.py                ← gestione database (foglia)
│   ├── date_filter.py               ← calendario trading (foglia)
│   └── deepseek_manager.py          ← analisi DeepSeek
│       └── db_manager.py            ← (già elencato)
├── deepseek_manager.py              ← (già elencato)
│   └── db_manager.py                ← (già elencato)
├── imf_validator.py                 ← validazione IMF
│   └── deepseek_manager.py          ← (già elencato)
└── db_manager.py                    ← (importato inline in main.py)
```

---

## 3. Flusso di Esecuzione

Quando si esegue `python main.py`, il programma segue questa sequenza:

```
UTENTE → Inserisce data (YYYY-MM-DD)
    │
    ▼
[1] fetcher.py → fetch_rss_news()
    Cerca notizie nei feed RSS di Reuters, CNBC, Investing.com
    │
    ├── SE trova notizie ──────────────────────────────┐
    │   │                                              │
    │   ▼                                              │
    │   [2] scraper.py → scrape_articles()             │
    │       Estrae titolo e corpo da HTML, pulisce      │
    │       il testo (rimozione stopword)              │
    │                                                  │
    ├── SE NON trova notizie ──────────────────────────┤
    │   │                                              │
    │   ▼                                              │
    │   [2b] archive_manager.py → selezione_intelligente()
    │        Interroga Perplexity AI (sonar-pro)        │
    │        per eventi storici nella data ±1-2 giorni  │
    │                                                  │
    ▼                                                  │
[3] new_store_articles2.py → store_articles() ◄────────┘
    │
    ├── Per ogni articolo e ogni indice:
    │   ├── date_filter.py → get_last_trading_day()
    │   ├── close_prev.py → get_close_prev()
    │   └── yfinance → download OHLCV
    │
    ├── main_filler.py → fill_dataframe()
    │   ├── core_addons.py → calc_core_addons_from_row()  [7 indicatori × 5 indici]
    │   └── extra_addons.py → calc_extra_addons()         [7 indicatori × 5 indici]
    │
    ├── db_manager.py → salva su database.xlsx
    │
    └── deepseek_manager.py → run_analysis_deepseek()
        Genera il report_nesso per ogni articolo
        (collegamento semantica ↔ numerico)
    │
    ▼
[4] deepseek_manager.py → run_lia_deepseek()
    Per ogni report_nesso:
    ├── trova_pattern_storici()         keyword matching nel DB
    └── analizza_pattern_mercato()      DeepSeek genera predizione UP/DOWN/NEUTRO
    │
    ▼
[5] imf_validator.py → run_imf_validation()
    Per ogni risultato LiA:
    ├── estrai_metriche_da_addons()     dalla riga del DB
    ├── classifica_shock()              confronto con soglie IMF
    └── valida_analisi_con_imf()        DeepSeek cross-check con benchmark IMF
    │
    ▼
OUTPUT → Report finale a terminale con:
         • Predizione (UP / DOWN / NEUTRO) e confidenza
         • Tipo di shock (moderato / rilevante / grave / nessuno)
         • Confronto con metriche IMF
         • Durata stimata degli effetti
```

---

## 4. Descrizione dei Moduli

### 4.1 `main.py` — Entry Point

Orchestratore centrale dell'intera pipeline. Chiede all'utente una data in formato `YYYY-MM-DD` e coordina tutte le fasi: raccolta notizie → scraping → salvataggio con prezzi → analisi pattern DeepSeek → validazione IMF.

**Import da progetto:** `fetcher`, `scraper`, `new_store_articles2`, `archive_manager`, `deepseek_manager`, `imf_validator`, `db_manager`.

**Logica principale:**
- Se i feed RSS restituiscono risultati → scraping + salvataggio.
- Se i feed sono vuoti → attiva `selezione_intelligente` (Perplexity) per trovare eventi storici.
- Dopo il salvataggio, ricarica il database per recuperare i `report_nesso` aggiornati e li passa a `run_lia_deepseek()` per l'analisi pattern, seguita da `run_imf_validation()`.

---

### 4.2 `fetcher.py` — Raccolta Notizie RSS

Interroga i feed RSS di tre fonti (Reuters, CNBC, Investing.com) e filtra le notizie per la data richiesta.

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `fetch_rss_news(rss_feeds, date_filter)` | Restituisce un DataFrame con colonne `Fonte`, `Titolo`, `Sintesi`, `Link`, `Data` |
| `print_prezzi_articolo(articolo)` | Stampa i prezzi Close dei 5 indici per un articolo |
| `print_notizia_e_prezzi(articolo)` | Stampa tutti i dati OHLCV + add-ons per un articolo |

**Librerie esterne:** `feedparser`, `pandas`.

---

### 4.3 `scraper.py` — Web Scraping Articoli

Esegue scraping mirato su pagine HTML di articoli da Reuters, CNBC e Investing.com. Include una fase di pulizia testo (`pulisci_testo`) che rimuove stopword, caratteri speciali e riduce il testo ai soli token significativi per favorire l'analisi semantica successiva.

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `scrape_articles(df)` | Per ogni riga del DataFrame, estrae e pulisce titolo + corpo |
| `scrape_article(source, url)` | Scraping specifico per fonte (Investing, CNBC, Reuters) |
| `pulisci_testo(testo)` | Rimozione stopword italiane, caratteri non alfabetici, spazi multipli |

**Librerie esterne:** `requests`, `beautifulsoup4`, `re`.

---

### 4.4 `archive_manager.py` — Selezione Intelligente (Perplexity)

Quando i feed RSS non restituiscono risultati per la data richiesta, questo modulo interroga l'API di **Perplexity AI** (modello `sonar-pro`) per trovare eventi geopolitici, economici o finanziari documentati. Cerca prima nella data esatta, poi nei giorni adiacenti (±1, ±2 giorni).

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `selezione_intelligente(date_str)` | Cerca eventi per la data richiesta e giorni vicini |
| `chiedi_articolo_perplexity(date_str)` | Chiamata singola a Perplexity API per una data specifica |

**Formato risposta Perplexity:** `TITOLO:`, `CORPO:`, `FONTI:` (2-3 URL separati da `;`).

**Librerie esterne:** `requests`, `datetime`, `dotenv`.

**Variabili d'ambiente:** `PERPLEXITY_API_KEY`.

---

### 4.5 `new_store_articles2.py` — Elaborazione e Salvataggio Articoli

Modulo centrale di elaborazione. Per ogni articolo ricevuto (da RSS o da Perplexity):

1. **Pulisce i dati** — normalizza titolo, corpo, fonti.
2. **Scarica dati di mercato** — per ciascuno dei 5 indici, tramite `yfinance`, individua l'ultimo trading day utile e scarica Open/High/Low/Close/Volume.
3. **Calcola Close_prev** — prezzo di chiusura del giorno di trading precedente.
4. **Riempie il DataFrame** — invoca `main_filler.fill_dataframe()` che calcola tutti gli indicatori core e extra.
5. **Salva su database.xlsx** — merge con dati esistenti, deduplicazione.
6. **Genera report_nesso** — invoca `deepseek_manager.run_analysis_deepseek()` per creare il collegamento semantica ↔ numerico per ogni articolo.

**Import da progetto:** `main_filler`, `close_prev`, `db_manager`, `date_filter`, `deepseek_manager`.

**Configurazione indici:**
```python
INDICI = {"SP500": "^GSPC", "NASDAQ": "^IXIC", "DAX": "^GDAXI", "FTSE100": "^FTSE", "NIKKEI": "^N225"}
CALENDARI = {"SP500": "XNYS", "NASDAQ": "XNYS", "DAX": "XFRA", "FTSE100": "XLON", "NIKKEI": "XTKS"}
```

---

### 4.6 `db_manager.py` — Gestione Database Excel

Gestisce la creazione e il percorso del database Excel (`database/database.xlsx`). Se il file non esiste, lo crea con tutte le 105 colonne necessarie (5 base + 20 per indice × 5 indici).

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `crea_database_se_necessario(filename)` | Crea il file Excel se mancante, restituisce il percorso assoluto |
| `get_database_dir()` | Restituisce il percorso della cartella `database/` |

**Costanti condivise:** `INDICI`, `CORE_ADDONS`, `EXTRA_ADDONS` (liste di stringhe per la generazione delle colonne).

---

### 4.7 `date_filter.py` — Calendari di Mercato e Trading Days

Utilizza `pandas_market_calendars` per determinare i giorni effettivi di apertura dei mercati. Fondamentale per evitare di cercare prezzi in giorni festivi o weekend.

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `get_last_trading_day(date_filter, market, window_days)` | Ultimo trading day ≤ alla data fornita |
| `get_next_trading_day(date_filter, market, window_days)` | Primo trading day > alla data fornita (per dati T+1) |
| `get_trading_days(date_filter, market, window_days)` | Lista di trading days negli ultimi N giorni |
| `get_trading_window(date_base, ticker, calendar_code, days)` | DataFrame con prezzi per gli ultimi N trading days |
| `get_rolling_window(date_filter, window)` | Finestra temporale (inizio, fine) per calcoli rolling |

**Calendari supportati:** XNYS (New York), XFRA (Francoforte), XLON (Londra), XTKS (Tokyo).

---

### 4.8 `close_prev.py` — Prezzo di Chiusura Precedente

Calcola il prezzo di chiusura del trading day immediatamente precedente alla data fornita. Questa è una metrica fondamentale perché molti indicatori (gap_ret, range_pct, true range) si basano sul confronto con la chiusura precedente.

**Funzione esportata:**
| Funzione | Descrizione |
|----------|-------------|
| `get_close_prev(date_str, calendar_code, ticker, df_prices)` | Restituisce il Close del giorno di trading precedente. Se è disponibile un DataFrame pre-scaricato (`df_prices`), cerca prima lì; altrimenti scarica da Yahoo Finance |

---

### 4.9 `main_filler.py` — Orchestratore Riempimento Dati

Fa da ponte tra i dati grezzi (OHLCV + Close_prev) e gli indicatori calcolati. Per ogni riga del DataFrame:

1. Calcola i **core add-ons** tramite `core_addons.py`.
2. Pre-scarica i **dati storici in batch** (con caching su disco in `ohlcv_cache/`) per efficienza.
3. Calcola gli **extra add-ons** tramite `extra_addons.py`, incluso il momentum forward (T+7).

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `fill_dataframe(df)` | Riempie l'intero DataFrame con tutti gli indicatori per tutte le righe |
| `fill_row(row, df, idx, hist_cache)` | Riempie una singola riga |
| `get_ohlcv_for_dates(dates, ticker, window)` | Recupera dati OHLCV storici con caching locale |

**Import da progetto:** `core_addons`, `extra_addons`, `close_prev`.

---

### 4.10 `core_addons.py` — Indicatori Finanziari Base

Calcola 7 indicatori per ciascuno dei 5 indici (35 colonne totali). Questi indicatori descrivono i movimenti giornalieri e la volatilità recente.

**Indicatori calcolati:**

| Indicatore | Formula / Descrizione |
|------------|----------------------|
| `gap_ret` | (Open − Close_prev) / Close_prev — gap di apertura |
| `intra_ret` | (Close − Open) / Open — rendimento intra-day |
| `range_pct` | (High − Low) / Close_prev — escursione percentuale |
| `tr` | True Range = max(H−L, |H−C_prev|, |L−C_prev|) |
| `atr7` | Media mobile del True Range su 7 giorni |
| `rv7` | Realized Volatility: √Σ(rendimenti²) su 7 giorni |
| `rs_vol7` | Volatilità Rogers-Satchell su 7 giorni |

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `calc_core_addons_from_row(row, df, idx)` | Calcola tutti i core add-ons per una singola riga |
| `calc_core_addons_from_df(df)` | Applica su tutto il DataFrame |

---

### 4.11 `extra_addons.py` — Indicatori Finanziari Avanzati

Calcola 7 indicatori aggiuntivi per ciascuno dei 5 indici (35 colonne totali). Include anche un sistema di fallback tramite Perplexity API per recuperare dati storici quando Yahoo Finance non è disponibile (date troppo remote).

**Indicatori calcolati:**

| Indicatore | Formula / Descrizione |
|------------|----------------------|
| `rolling_min7` | Minimo rolling su 7 giorni |
| `rolling_max7` | Massimo rolling su 7 giorni |
| `zscore7` | (Close − media_7g) / std_7g — distanza dalla media in σ |
| `percentile7` | Posizione percentile nel range dei 7 giorni |
| `drawdown` | (Close − massimo_storico) / massimo_storico — sempre ≤ 0 |
| `momentum7` | Close_T+7 − Close_T (forward-looking: impatto a 7 giorni) |
| `volatility7` | Std dei rendimenti logaritmici rolling su 7 giorni |

**Funzionalità aggiuntive:**
- **Caching dati storici** — `fetch_historical_batch()` scarica e memorizza dati OHLCV in `ohlcv_cache/` (formato pickle).
- **Fallback Perplexity** — `fetch_historical_prices_perplexity()` interroga Perplexity AI per recuperare prezzi storici quando yfinance fallisce.
- **Momentum forward** — `calc_momentum_forward()` e `get_close_t7()` calcolano il prezzo a T+7 per misurare l'impatto effettivo dell'evento sui mercati nei giorni successivi.

---

### 4.12 `deepseek_manager.py` — Analisi Pattern con DeepSeek AI

Il modulo di intelligenza artificiale principale del sistema. Utilizza l'API di **DeepSeek** (`deepseek-chat`) e svolge due funzioni distinte:

#### Funzione A — Analisi Incrementale (`run_analysis_deepseek`)

Per ogni articolo, genera un **report_nesso**: un testo sintetico (max 3 righe) che collega il contenuto semantico della notizia ai movimenti osservati nei dati di mercato (prezzi + add-ons). Il report viene salvato nella colonna `report_nesso` del database.

#### Funzione B — Pattern Matching LiA (`run_lia_deepseek`)

Per ogni `report_nesso`:
1. **Trova pattern storici** — `trova_pattern_storici()` confronta le parole chiave (> 4 caratteri) del report nuovo con tutti i report storici nel database, contando le parole in comune.
2. **Conta UP/DOWN** — per ogni match storico, verifica se l'S&P 500 è salito o sceso (Close vs Close_prev).
3. **Genera predizione** — DeepSeek analizza i pattern e produce una predizione (UP / DOWN / NEUTRO) con livello di confidenza.

**Funzioni esportate:**
| Funzione | Descrizione |
|----------|-------------|
| `call_deepseek(prompt, max_tokens, temperature)` | Wrapper generico per le chiamate API DeepSeek |
| `run_analysis_deepseek(articoli_completi)` | Analisi incrementale → genera report_nesso |
| `run_lia_deepseek(report_nesso_list)` | Pattern matching + predizione UP/DOWN |
| `analizza_pattern_mercato(report_nesso_nuovo)` | Analisi singolo report vs database storico |
| `trova_pattern_storici(report_nesso, soglia)` | Ricerca keyword-matching nel database |

---

### 4.13 `imf_validator.py` — Validazione con Metriche IMF

Ultimo step della pipeline. Confronta i risultati dell'analisi LiA con le metriche di riferimento pubblicate dal Fondo Monetario Internazionale per shock geopolitici e finanziari.

**Processo di validazione:**
1. **Estrazione metriche** — per ogni indice estrae: variazione giornaliera, gap apertura, drawdown, zscore7, volatilità, momentum, atr7.
2. **Classificazione automatica dello shock:**

   | Classificazione | Condizioni |
   |-----------------|------------|
   | `SHOCK_FINANZIARIO_GRAVE` | drawdown > 10% oppure calo medio > 3% |
   | `SHOCK_GEOPOLITICO_RILEVANTE` | drawdown > 3% oppure calo medio > 1.5% oppure zscore < −2 |
   | `SHOCK_GEOPOLITICO_MODERATO` | calo medio > 0.5% oppure zscore < −1 |
   | `NESSUNO_SHOCK_RILEVATO` | nessuna condizione sopra soddisfatta |

3. **Cross-check con DeepSeek** — un prompt strutturato fornisce a DeepSeek le metriche IMF di riferimento (cali medi mensili, premi di rischio, soglie giornaliere/settimanali) e chiede conferma o rettifica della classificazione automatica, con previsione di durata e livello di allerta.

**Benchmark IMF integrati:**
- Calo medio mensile azionario globale per shock geopolitici: ~1%
- Calo medio mercati emergenti in tensioni geopolitiche: fino a ~2.5%
- Aumento premi rischio sovrano: ~30bp (avanzate), ~45bp (emergenti)
- Shock finanziari gravi: correzioni cumulative > 10-20%

---

## 5. Schema del Database

Il database è un file Excel (`database/database.xlsx`) generato automaticamente da `db_manager.py`. Contiene **105 colonne**:

```
COLONNE BASE (5):
  Data | Titolo | Corpo | Fonti | report_nesso

PER OGNI INDICE (×5: SP500, NASDAQ, DAX, FTSE100, NIKKEI):

  OHLCV (6 colonne):
    {INDICE}_Open
    {INDICE}_High
    {INDICE}_Low
    {INDICE}_Close
    {INDICE}_Volume
    {INDICE}_Close_prev

  Core Add-ons (7 colonne):
    {INDICE}_gap_ret
    {INDICE}_intra_ret
    {INDICE}_range_pct
    {INDICE}_tr
    {INDICE}_atr7
    {INDICE}_rv7
    {INDICE}_rs_vol7

  Extra Add-ons (7 colonne):
    {INDICE}_rolling_min7
    {INDICE}_rolling_max7
    {INDICE}_zscore7
    {INDICE}_percentile7
    {INDICE}_drawdown
    {INDICE}_momentum7
    {INDICE}_volatility7

TOTALE: 5 + (5 × 20) = 105 colonne
```

---

## 6. Add-ons Finanziari

### Core Add-ons (7 per indice)

| # | Indicatore | Tipo | Finestra | Significato |
|---|-----------|------|----------|-------------|
| 1 | `gap_ret` | Rendimento | 1 giorno | Misura il "salto" tra chiusura precedente e apertura. Un gap negativo ampio segnala vendite overnight (panico, notizie notturne). |
| 2 | `intra_ret` | Rendimento | 1 giorno | Misura la direzione del mercato durante la sessione di trading. |
| 3 | `range_pct` | Escursione | 1 giorno | Ampiezza della barra giornaliera normalizzata. Valori alti = sessione volatile. |
| 4 | `tr` | Volatilità | 1 giorno | True Range: la maggiore escursione tra High-Low, High-Close_prev, Low-Close_prev. |
| 5 | `atr7` | Volatilità | 7 giorni | Media mobile del True Range. Indica la volatilità "normale" recente. |
| 6 | `rv7` | Volatilità | 7 giorni | Realized Volatility: radice della somma dei rendimenti al quadrato. Più reattiva dell'ATR. |
| 7 | `rs_vol7` | Volatilità | 7 giorni | Volatilità Rogers-Satchell: utilizza Open, High, Low, Close per una stima efficiente. |

### Extra Add-ons (7 per indice)

| # | Indicatore | Tipo | Finestra | Significato |
|---|-----------|------|----------|-------------|
| 1 | `rolling_min7` | Supporto | 7 giorni | Minimo prezzo nei 7 giorni precedenti. Livello di supporto. |
| 2 | `rolling_max7` | Resistenza | 7 giorni | Massimo prezzo nei 7 giorni precedenti. Livello di resistenza. |
| 3 | `zscore7` | Posizionamento | 7 giorni | Quante deviazioni standard il prezzo corrente dista dalla media. zscore < −2 = potenziale shock. |
| 4 | `percentile7` | Posizionamento | 7 giorni | Posizione percentuale nel range dei 7 giorni. |
| 5 | `drawdown` | Rischio | Cumulativo | Distanza percentuale dal massimo storico. Sempre ≤ 0. |
| 6 | `momentum7` | Impatto | T+7 (forward) | Close a T+7 − Close a T. Misura l'impatto reale dell'evento a una settimana. |
| 7 | `volatility7` | Rischio | 7 giorni | Deviazione standard dei rendimenti logaritmici rolling. |

---

## 7. API e Modelli AI Utilizzati

| Servizio | Modello | Utilizzato in | Scopo |
|----------|---------|---------------|-------|
| **DeepSeek** | `deepseek-chat` | `deepseek_manager.py`, `imf_validator.py` | Analisi report_nesso, pattern matching, predizioni, validazione IMF |
| **Perplexity** | `sonar-pro` | `archive_manager.py`, `extra_addons.py` | Ricerca eventi storici con fonti verificate, fallback dati prezzi storici |
| **Yahoo Finance** | — | `new_store_articles2.py`, `close_prev.py`, `date_filter.py`, `extra_addons.py`, `main_filler.py` | Download dati OHLCV reali |

---

## 8. Installazione e Avvio

### Prerequisiti

- Python 3.10+
- Chiavi API: DeepSeek e Perplexity (configurate in file `.env`)

### Installazione

```bash
# 1. Clona il progetto
git clone <repository-url>
cd LinkedIA-main

# 2. Installa le dipendenze
pip install -r requirements.txt

# 3. Configura le variabili d'ambiente
# Crea un file .env nella root del progetto:
PERPLEXITY_API_KEY=la_tua_chiave_perplexity
DEEPSEEK_API_KEY=la_tua_chiave_deepseek
OPENAI_API_KEY=la_tua_chiave_openai   # opzionale, usato solo da moduli legacy
```

### Avvio

```bash
python main.py
```

Il programma chiederà una data in formato `YYYY-MM-DD` e avvierà automaticamente l'intera pipeline.

### Output atteso

```
Inserisci la data (YYYY-MM-DD): 2022-02-24

Nessuna notizia trovata nei feed RSS per la data inserita.
Attivo la selezione intelligente...

Data: 2022-02-24
Titolo: russia invade ucraina escalation conflitto armato
Fonti: https://...

✅ Articoli elaborati e salvati su database/database.xlsx

--- ANALISI LiA DeepSeek (Pattern Matching + AI) ---
 Predizione: DOWN (confidenza: 78.5%)
 Statistiche storiche: 2 UP, 7 DOWN

VALIDAZIONE IMF
 Tipo di shock: SHOCK GEOPOLITICO RILEVANTE
 Calo medio giornaliero: 2.15%
 Durata stimata: settimane/mesi
 Livello di allerta: ALTO
```

---

## 9. Limitazioni e Sviluppi Futuri

### Limitazioni attuali

| Area | Limitazione |
|------|-------------|
| **Database** | File Excel — non scalabile per grandi volumi di dati |
| **Fonti notizie** | Solo feed RSS gratuiti (Reuters, CNBC, Investing). Qualità e copertura variabili |
| **Pattern matching** | Basato su keyword matching (parole > 4 caratteri). Non utilizza embedding semantici |
| **Sicurezza** | La chiave API DeepSeek è hardcoded in `deepseek_manager.py` — da spostare in `.env` |

### Possibili sviluppi

- Migrazione a database relazionale (PostgreSQL) o vettoriale (Pinecone) per ricerche semantiche
- Integrazione fonti premium (Bloomberg, Factiva, Refinitiv)
- Sostituzione keyword matching con embedding (sentence-transformers) per similarità più accurata
- Backtesting sistematico delle predizioni LiA su dati storici
- Dashboard web interattiva (frontend React e Vue già presenti ma non collegati a `main.py`)

---

> **Disclaimer:** LinkedIA è un prototipo sperimentale a scopo accademico. Non costituisce consulenza finanziaria. I mercati sono imprevedibili e le performance passate non garantiscono risultati futuri.
