# LinkedIA - Linked Intelligent Analyst 🤖📈

**Dove notizie e mercati si incontrano**

LinkedIA è un prototipo sperimentale di intelligenza artificiale che analizza notizie finanziarie in tempo reale, le collega ai dati storici di mercato e genera insight predittivi.

## 🎯 Descrizione del Progetto

Un sistema innovativo che unisce:
- **Analisi del linguaggio naturale** - Elaborazione semantica delle notizie geopolitiche e finanziarie
- **Analisi dei prezzi di mercato** - Dati OHLCV da indici principali (SP500, NASDAQ, DAX, FTSE100, NIKKEI)
- **Indicatori avanzati** - Core add-ons e extra add-ons per l'analisi tecnica
- **Connessione semantica-numerica** - Sistema di nessi tra eventi e movimenti di mercato

## 🏗️ Architettura del Sistema

### Moduli Principali

1. **fetcher.py** - Raccolta notizie da feed RSS
2. **scraper.py** - Web scraping per dettagli articoli
3. **archive_manager.py** - Ricerca eventi storici via GPT-3.5-turbo
4. **date_filter.py** - Gestione calendari di mercato e trading days
5. **close_prev.py** - Calcolo prezzi di chiusura precedenti
6. **core_addons.py** - Calcolo indicatori finanziari base (gap_ret, intra_ret, ATR, volatility, ecc.)
7. **extra_addons.py** - Indicatori avanzati (rolling statistics, zscore, drawdown, momentum)
8. **analizer2.py** - Analisi incrementale con collegamento notizie-prezzi
9. **LiA.py** - Core dell'AI: analisi finale con TF-IDF e similarità coseno
10. **db_manager.py** - Gestione database Excel
11. **main.py** - Orchestrazione dell'intero flusso

### Struttura Dati

```
database/
└── database.xlsx  # Database principale con colonne:
    ├── Metadati: Data, Titolo, Corpo, Fonti, report_nesso
    ├── Prezzi OHLCV per 5 indici
    ├── Core add-ons (7 metriche per indice)
    └── Extra add-ons (7 metriche per indice)
```

## 🚀 Quick Start

### Prerequisiti

- Python 3.10+
- Chiave API OpenAI

### Installazione

```bash
# 1. Clone/Download del progetto
cd LinkedIA

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Configura chiave OpenAI
# IMPORTANTE: Sostituisci la chiave hardcoded nei file con una variabile d'ambiente
# Crea un file .env e aggiungi:
# OPENAI_API_KEY=your_key_here

# 4. Esegui il programma
python main.py
```

### Utilizzo Base

```bash
# Inserisci una data nel formato YYYY-MM-DD
python main.py
> Inserisci la data (YYYY-MM-DD): 2022-02-24

# Il sistema:
# 1. Cerca notizie nei feed RSS per quella data
# 2. Se non trova notizie, attiva la "selezione intelligente" (GPT)
# 3. Scarica prezzi di mercato e calcola add-ons
# 4. Analizza i nessi tra notizie e mercati
# 5. Genera report finale con LiA
```

## 🧮 Add-ons Finanziari

### Core Add-ons (7 metriche)
- **gap_ret**: Gap return (open vs close precedente)
- **intra_ret**: Intraday return
- **range_pct**: Range percentuale
- **tr**: True Range
- **atr7**: Average True Range (7 giorni)
- **rv7**: Realized Volatility (7 giorni)
- **rs_vol7**: Rogers-Satchell Volatility (7 giorni)

### Extra Add-ons (7 metriche)
- **rolling_min7/max7**: Min/Max rolling 7 giorni
- **zscore7**: Z-score (7 giorni)
- **percentile7**: Percentile (7 giorni)
- **drawdown**: Drawdown dal picco
- **momentum7**: Momentum (7 giorni)
- **volatility7**: Volatilità rolling (7 giorni)

## 🔍 Funzionalità Chiave

### 1. Selezione Intelligente
Quando mancano notizie nei feed RSS, il sistema interroga GPT-3.5-turbo per trovare eventi storici rilevanti nel periodo ±14 giorni dalla data richiesta.

### 2. Analisi Incrementale
Per ogni notizia trovata, `analizer2.py` genera un **report_nesso** che collega:
- Contenuto semantico della notizia
- Dati di prezzo OHLCV
- Valori degli add-ons
- Interpretazione dell'impatto sul mercato

### 3. LiA - Analisi Finale
Il modulo `LiA.py` usa:
- **TF-IDF Vectorization** per rappresentare i report_nesso
- **Cosine Similarity** per trovare pattern storici simili
- **GPT-3.5-turbo** per generare sentenze predittive

## ⚠️ Note Importanti

### Sicurezza
🔴 **CRITICO**: Le chiavi API OpenAI sono attualmente hardcoded nel codice. Prima di usare in produzione:
```python
# Sostituisci in tutti i file:
# openai.api_key = "sk-proj-..."
# Con:
import os
openai.api_key = os.getenv("OPENAI_API_KEY")
```

### Limitazioni Attuali
- Database Excel (non scalabile per grandi volumi)
- Dipendenza da feed RSS gratuiti (qualità variabile)
- Soglia di similarità in `LiA.py` fissata a 0.0 (da ottimizzare)
- Funzione `get_trading_window` in `date_filter.py` parzialmente inutilizzata

### Ottimizzazioni Future
- Migrare a database relazionale (PostgreSQL) o vettoriale (Pinecone)
- Integrare fonti premium (Bloomberg, Factiva, Refinitiv)
- Implementare caching per ridurre chiamate API
- Aggiungere backtesting e validazione statistica
- Dashboard interattiva con visualizzazioni

## 📊 Output Esempio

```
Data: 2022-02-24
Titolo: Russia invade l'Ucraina
Fonti: Reuters; Bloomberg; Financial Times

PREZZI: {SP500_Close: 4348.87, SP500_gap_ret: -0.027, ...}
ADD-ONS: {SP500_atr7: 67.32, SP500_rv7: 0.19, ...}

REPORT NESSO (analizer2.py):
L'invasione russa dell'Ucraina ha causato un gap down del 2.7% sull'S&P500 
all'apertura. L'ATR è salito a 67 punti, indicando volatilità estrema. 
Il report evidenzia fuga verso beni rifugio e crollo titoli ciclici.

SENTENZA LiA:
Pattern simili a crisi geopolitiche del 2014 (Crimea) e 2001 (9/11). 
Atteso rimbalzo tecnico entro 3-5 sedute con volatilità elevata persistente 
per 2-3 settimane. Settori difensivi sovraperformanti.
```

## 🤝 Contributi

Questo è un prototipo accademico sviluppato per tesi di laurea. Feedback e suggerimenti sono benvenuti!

## 📝 Licenza

Progetto accademico - Università del Piemonte Orientale (UNIUPO)

## 📧 Contatti

Autore: Marco
Università: UNIUPO - Corso di Laurea

---

**⚠️ Disclaimer**: Questo sistema è un prototipo sperimentale a scopo educativo. Non costituisce consulenza finanziaria. I mercati sono imprevedibili e le performance passate non garantiscono risultati futuri.
