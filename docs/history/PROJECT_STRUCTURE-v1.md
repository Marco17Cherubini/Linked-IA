# LinkedIA Project Structure

LinkedIA/
│
├── 📄 main.py                    # Entry point - orchestrazione flusso principale
├── 📄 LiA.py                     # Core AI - analisi finale con TF-IDF e similarità
│
├── 📁 Data Collection
│   ├── fetcher.py                # Raccolta notizie da feed RSS
│   ├── scraper.py                # Web scraping dettagli articoli
│   └── archive_manager.py        # Ricerca eventi storici via GPT
│
├── 📁 Market Data Processing
│   ├── date_filter.py            # Gestione calendari mercato e trading days
│   ├── close_prev.py             # Calcolo prezzi chiusura precedenti
│   ├── core_addons.py            # Indicatori finanziari base
│   └── extra_addons.py           # Indicatori avanzati
│
├── 📁 Analysis & Intelligence
│   ├── analizer2.py              # Analisi incrementale notizie-prezzi
│   └── db_manager.py             # Gestione database Excel
│
├── 📁 Web Interface
│   ├── server.py                 # Flask web server
│   ├── index.html                # Frontend UI
│   └── style.css                 # Styling
│
├── 📁 Configuration
│   ├── requirements.txt          # Dipendenze Python
│   ├── .env.example              # Template variabili ambiente
│   ├── .gitignore                # File da escludere da Git
│   └── setup.py                  # Setup wizard
│
├── 📁 Data Storage
│   └── database/
│       └── database.xlsx         # Database principale (generato automaticamente)
│
└── 📄 README.md                  # Documentazione completa

## Flusso di Esecuzione

1. USER INPUT → main.py
   ↓
2. FETCH NEWS → fetcher.py (RSS feeds)
   ↓ (se vuoto)
3. INTELLIGENT SEARCH → archive_manager.py (GPT-3.5)
   ↓
4. SCRAPE DETAILS → scraper.py
   ↓
5. GET MARKET DATA → date_filter.py + yfinance
   ↓
6. CALCULATE ADD-ONS → core_addons.py + extra_addons.py
   ↓
7. INCREMENTAL ANALYSIS → analizer2.py (nessi semantica-numerico)
   ↓
8. STORE DATA → db_manager.py (Excel database)
   ↓
9. FINAL ANALYSIS → LiA.py (TF-IDF + Cosine Similarity + GPT)
   ↓
10. OUTPUT → Report finale con previsioni

## Database Schema (database.xlsx)

Colonne Base:
- Data, Titolo, Corpo, Fonti, report_nesso

Per ogni indice (SP500, NASDAQ, DAX, FTSE100, NIKKEI):

OHLCV (6 colonne):
- {INDICE}_Open
- {INDICE}_High
- {INDICE}_Low
- {INDICE}_Close
- {INDICE}_Volume
- {INDICE}_Close_prev

Core Add-ons (7 colonne):
- {INDICE}_gap_ret
- {INDICE}_intra_ret
- {INDICE}_range_pct
- {INDICE}_tr
- {INDICE}_atr7
- {INDICE}_rv7
- {INDICE}_rs_vol7

Extra Add-ons (7 colonne):
- {INDICE}_rolling_min7
- {INDICE}_rolling_max7
- {INDICE}_zscore7
- {INDICE}_percentile7
- {INDICE}_drawdown
- {INDICE}_momentum7
- {INDICE}_volatility7

TOTALE: 5 + (5 × 20) = 105 colonne
