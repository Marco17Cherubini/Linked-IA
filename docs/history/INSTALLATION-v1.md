# LinkedIA - Installation & Setup Guide

## 🎯 Installazione Completa

### Passo 1: Verifica Prerequisiti

```bash
# Verifica versione Python (richiesto 3.10+)
python --version

# Output atteso: Python 3.13.3 (o superiore a 3.10)
```

### Passo 2: Installazione Dipendenze

Tutte le dipendenze principali sono già installate nel tuo ambiente:

✅ **Già Installate:**
- pandas (2.2.3)
- numpy (2.2.5)
- yfinance (0.2.65)
- pandas_market_calendars (5.1.1)
- scikit-learn (1.7.1)
- openai (0.28.0)
- feedparser (6.0.11)
- beautifulsoup4 (4.13.4)
- Flask (3.1.2)
- openpyxl (3.1.5)

Se dovessi reinstallare:

```bash
pip install -r requirements.txt
```

### Passo 3: Configurazione API Key OpenAI

#### Opzione A: Setup Automatico (Raccomandato)

```bash
python setup.py
```

Segui il wizard interattivo che:
1. Crea il file `.env`
2. Richiede la tua chiave OpenAI API
3. Verifica le dipendenze

#### Opzione B: Configurazione Manuale

1. Copia il file template:
```bash
copy .env.example .env
```

2. Modifica `.env` con la tua chiave:
```
OPENAI_API_KEY=sk-proj-your_actual_key_here
```

3. **IMPORTANTE**: Modifica i file Python per usare la variabile d'ambiente:

**In `archive_manager.py`, `analizer2.py`, `LiA.py`:**

Sostituisci:
```python
openai.api_key = ("sk-proj-DGIPN88y6aFwNuQqh83_kUqCGFG...")
```

Con:
```python
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
```

Installa python-dotenv se necessario:
```bash
pip install python-dotenv
```

### Passo 4: Verifica Installazione

```bash
python start.py
```

Questo script esegue controlli automatici su:
- Versione Python
- File .env
- Directory database
- Sicurezza API keys

## 🚀 Avvio del Sistema

### Metodo 1: Script di Avvio (Raccomandato)

```bash
python start.py
```

Esegue tutti i controlli e avvia `main.py` automaticamente.

### Metodo 2: Avvio Diretto

```bash
python main.py
```

Inserisci una data quando richiesto:
```
Inserisci la data (YYYY-MM-DD): 2022-02-24
```

## 📋 Struttura File Dopo Setup

```
LinkedIA/
├── .env                    # ✅ Creato - Chiavi API (NON committare!)
├── .env.example            # ✅ Template per .env
├── .gitignore              # ✅ Esclude file sensibili
├── requirements.txt        # ✅ Dipendenze Python
├── README.md               # ✅ Documentazione completa
├── PROJECT_STRUCTURE.md    # ✅ Architettura sistema
├── INSTALLATION.md         # ✅ Questa guida
├── setup.py                # ✅ Setup wizard
├── start.py                # ✅ Script avvio con controlli
│
├── main.py                 # Entry point
├── LiA.py                  # Core AI
├── archive_manager.py      # Ricerca storica GPT
├── analizer2.py            # Analisi incrementale
├── fetcher.py              # RSS feed collector
├── scraper.py              # Web scraper
├── date_filter.py          # Market calendars
├── close_prev.py           # Previous close calculator
├── core_addons.py          # Core indicators
├── extra_addons.py         # Extra indicators
├── db_manager.py           # Database manager
│
├── server.py               # Flask server
├── index.html              # Web UI
├── style.css               # Styling
│
└── database/
    └── database.xlsx       # ✅ Creato automaticamente al primo avvio
```

## 🔧 Troubleshooting

### Problema: "ModuleNotFoundError"

```bash
# Reinstalla le dipendenze
pip install -r requirements.txt
```

### Problema: "OpenAI API Error"

Verifica che:
1. La chiave API sia corretta nel file `.env`
2. Hai crediti disponibili nel tuo account OpenAI
3. La chiave non sia scaduta

```python
# Test chiave API
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Prova una chiamata semplice
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

### Problema: "No trading data found"

Possibili cause:
1. Data inserita è un weekend o festivo
2. Mercati erano chiusi quel giorno
3. Ticker non esistente per quella data

Soluzione: Prova con una data recente in un giorno feriale (es. lunedì-venerdì).

### Problema: Database Excel corrotto

```bash
# Elimina e ricrea il database
rmdir /s database
python main.py  # Creerà automaticamente un nuovo database
```

## 🎓 Esempi di Utilizzo

### Esempio 1: Analisi Evento Storico

```bash
python main.py
> Inserisci la data (YYYY-MM-DD): 2022-02-24

# Analizza l'invasione russa dell'Ucraina
```

### Esempio 2: Crisi Finanziaria

```bash
python main.py
> Inserisci la data (YYYY-MM-DD): 2008-09-15

# Analizza il fallimento di Lehman Brothers
```

### Esempio 3: Pandemia COVID-19

```bash
python main.py
> Inserisci la data (YYYY-MM-DD): 2020-03-16

# Analizza il crollo dei mercati durante la pandemia
```

## 📊 Output Attesi

Il sistema genererà:

1. **Console Output**: Notizie trovate, prezzi, add-ons, report nessi
2. **Database Update**: Nuovo record in `database/database.xlsx`
3. **LiA Analysis**: Sentenza finale con pattern storici e previsioni

## 🔐 Sicurezza

### Best Practices:

1. **Mai committare `.env`** su Git (già in `.gitignore`)
2. **Ruota le chiavi API** regolarmente
3. **Usa variabili d'ambiente** in produzione
4. **Limita i permessi** del file .env:

```bash
# Solo su Linux/Mac
chmod 600 .env
```

## 📚 Prossimi Passi

Dopo l'installazione:

1. Leggi `README.md` per comprendere l'architettura
2. Esplora `PROJECT_STRUCTURE.md` per capire il flusso
3. Testa con date storiche note
4. Analizza l'output in `database/database.xlsx`
5. Personalizza i prompts in `archive_manager.py` e `analizer2.py`

## 🆘 Supporto

Per problemi o domande:
- Controlla i log nella console
- Verifica errori in `database/database.xlsx`
- Rivedi questa guida INSTALLATION.md
- Contatta il maintainer del progetto

---

**Ultima revisione**: Ottobre 2025
**Versione Python**: 3.13.3
**Sistema**: Windows con PowerShell
