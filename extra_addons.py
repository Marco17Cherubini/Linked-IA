import numpy as np  # libreria per il calcolo scientifico, utile per operazioni numeriche avanzate
import pandas as pd  # libreria per la manipolazione dei dati, consente di lavorare con DataFrame
import yfinance as yf  # libreria per scaricare dati finanziari da Yahoo Finance
import os  # libreria per operazioni su file e directory
import pickle  # libreria per caching
import requests  # libreria per chiamate HTTP all'API di Perplexity
import json  # libreria per parsing JSON
import re  # libreria per regex
from dotenv import load_dotenv  # per caricare variabili d'ambiente dal file .env

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# --- Configurazione API Perplexity ---
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_BASE_URL = "https://api.perplexity.ai/chat/completions"

# --- Cache per dati storici ---
CACHE_DIR = 'ohlcv_cache'
PERPLEXITY_CACHE_DIR = 'cache_perplexity_finance'

def fetch_historical_batch(dates, tickers, window=30):
    """
    Scarica dati storici per più date e ticker con caching.
    Window default = 30 giorni per garantire almeno 14 trading days.
    Ritorna un dict: {ticker_name: DataFrame con OHLCV}
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    result = {}
    
    for name, ticker in tickers.items():
        cache_file = os.path.join(CACHE_DIR, f'{name}_hist.pkl')
        
        # Carica cache esistente
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                cached_df = pickle.load(f)
        else:
            cached_df = pd.DataFrame()
        
        # Determina range di date necessario
        all_dates = [pd.to_datetime(d) for d in dates]
        if not all_dates:
            result[name] = cached_df
            continue
        
        # Aumenta buffer per garantire 14+ trading days (considerando weekend/festivi)
        min_date = min(all_dates) - pd.Timedelta(days=window)
        max_date = max(all_dates) + pd.Timedelta(days=5)
        
        # Scarica solo se necessario
        need_download = cached_df.empty
        if not cached_df.empty:
            cached_df.index = pd.to_datetime(cached_df.index)
            if cached_df.index.min() > min_date or cached_df.index.max() < max_date:
                need_download = True
        
        if need_download:
            try:
                df = yf.download(ticker, start=min_date.strftime('%Y-%m-%d'), 
                               end=(max_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d'),
                               progress=False, auto_adjust=True)
                if not df.empty:
                    # Gestione colonne MultiIndex da yfinance
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    cached_df = df
                    with open(cache_file, 'wb') as f:
                        pickle.dump(cached_df, f)
            except Exception as e:
                print(f"Errore download {name}: {e}")
        
        result[name] = cached_df
    
    return result

def get_window(df, ref_date, window=7):
    """
    Estrae gli ultimi 'window' giorni di dati fino a ref_date (incluso).
    Ritorna DataFrame con colonne OHLCV standard.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    ref_date = pd.to_datetime(ref_date)
    
    # Filtra fino a ref_date e prendi ultimi 'window' giorni
    df_filtered = df[df.index <= ref_date].sort_index()
    window_df = df_filtered.tail(window)
    
    return window_df

# Funzione per estrarre la finestra storica utile agli extra add-ons
def get_window_for_addons(df, date_col='Data', close_col='Close', ref_date=None, window=7):
    """
    Restituisce la finestra degli ultimi 'window' giorni di Close fino a ref_date.
    df deve contenere almeno le colonne [date_col, close_col].
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    ref_date = pd.to_datetime(ref_date)
    # Filtra solo le righe con data <= ref_date, ordina per data
    df = df[df[date_col] <= ref_date].sort_values(date_col)
    # Prendi solo le ultime 'window' righe
    window_df = df.tail(window)
    # Rinomina la colonna Close se necessario
    window_df = window_df.rename(columns={close_col: 'Close'})
    return window_df

def calc_rolling_min(series, window=7):
    """Calcola il rolling minimo su una finestra di n giorni."""
    if len(series) < 1:
        return np.nan
    return series.rolling(window=window, min_periods=1).min()

def calc_rolling_max(series, window=7):
    """Calcola il rolling massimo su una finestra di n giorni."""
    if len(series) < 1:
        return np.nan
    return series.rolling(window=window, min_periods=1).max()

def calc_zscore(series, window=7):
    """Calcola lo z-score su una finestra di n giorni."""
    if len(series) < 2:
        return pd.Series([np.nan] * len(series), index=series.index)
    mean = series.rolling(window=window, min_periods=2).mean()
    std = series.rolling(window=window, min_periods=2).std(ddof=0)
    # Evita divisione per zero
    std = std.replace(0, np.nan)
    return (series - mean) / std

def calc_percentile(series, window=7):
    """Calcola il percentile rank su una finestra di n giorni.
    Restituisce la posizione percentuale del valore corrente rispetto alla finestra.
    """
    if len(series) < 1:
        return pd.Series([np.nan] * len(series), index=series.index)
    
    def percentile_rank(x):
        if len(x) < 2:
            return np.nan
        current = x[-1]
        # Conta quanti valori sono minori del valore corrente
        below = np.sum(x[:-1] < current)
        # Percentile = (valori sotto) / (totale valori - 1)
        return below / (len(x) - 1)
    
    return series.rolling(window=window, min_periods=2).apply(percentile_rank, raw=True)

def calc_drawdown(series):
    """Calcola il drawdown percentuale dal massimo storico.
    Drawdown = (valore corrente - massimo storico) / massimo storico
    Sempre <= 0 (negativo o zero se al massimo).
    """
    if len(series) < 1:
        return pd.Series([np.nan] * len(series), index=series.index)
    
    # Calcola il massimo cumulativo fino a ogni punto
    cummax = series.expanding(min_periods=1).max()
    
    # Evita divisione per zero
    cummax_safe = cummax.replace(0, np.nan)
    
    # Drawdown = (current - max) / max
    drawdown = (series - cummax_safe) / cummax_safe
    
    return drawdown

def calc_momentum(series, window=7):
    """Calcola il momentum come differenza tra valore attuale e n giorni fa.
    NOTA: Per analisi impatto notizie, usare calc_momentum_forward() che calcola T+7 - T.
    """
    if len(series) < window + 1:
        # Non abbastanza dati per calcolare momentum completo
        return pd.Series([np.nan] * len(series), index=series.index)
    return series - series.shift(window)


def calc_momentum_forward(close_t, close_t7):
    """Calcola il momentum forward: Close[T+7] - Close[T].
    Misura l'impatto sui prezzi 7 giorni DOPO la notizia.
    
    Args:
        close_t: Prezzo di chiusura alla data della notizia
        close_t7: Prezzo di chiusura 7 giorni dopo
    
    Returns:
        Momentum forward (positivo = prezzo salito, negativo = prezzo sceso)
    """
    if pd.isna(close_t) or pd.isna(close_t7):
        return np.nan
    return close_t7 - close_t

def calc_volatility(series, window=7):
    """Calcola la volatilità rolling su n giorni (std dei rendimenti logaritmici)."""
    if len(series) < 2:
        return pd.Series([np.nan] * len(series), index=series.index)
    # Evita log di valori <= 0
    series_safe = series.replace(0, np.nan)
    shifted = series_safe.shift(1)
    # Evita divisione per zero o valori negativi nel log
    ratio = series_safe / shifted
    ratio = ratio.where(ratio > 0, np.nan)
    log_ret = np.log(ratio)
    return log_ret.rolling(window=window, min_periods=2).std(ddof=0)

# Funzione wrapper per calcolare tutti gli extra add-ons su una riga/df
def calc_extra_addons(df):
    """
    Calcola tutti gli extra add-ons e li aggiunge al DataFrame.
    Richiede colonna 'Close' nel DataFrame.
    """
    df = df.copy()
    
    # Verifica che la colonna Close esista e abbia valori validi
    if 'Close' not in df.columns:
        # Ritorna DataFrame con colonne vuote
        for col in ['rolling_min7', 'rolling_max7', 'zscore7', 'percentile7', 
                    'drawdown', 'momentum7', 'volatility7']:
            df[col] = np.nan
        return df
    
    # Converti Close a numerico, gestendo valori non validi
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    close_series = df['Close']
    
    # Calcola tutti gli add-ons
    df['rolling_min7'] = calc_rolling_min(close_series, window=7)
    df['rolling_max7'] = calc_rolling_max(close_series, window=7)
    df['zscore7'] = calc_zscore(close_series, window=7)
    df['percentile7'] = calc_percentile(close_series, window=7)
    df['drawdown'] = calc_drawdown(close_series)
    df['momentum7'] = calc_momentum(close_series, window=7)
    df['volatility7'] = calc_volatility(close_series, window=7)
    
    return df

# --- PERPLEXITY API per recupero dati storici mancanti ---

def fetch_historical_prices_perplexity(index_name, ref_date, days_needed=14):
    """
    Usa Perplexity API per recuperare prezzi di chiusura storici quando yfinance fallisce.
    
    Args:
        index_name: Nome indice (es. 'SP500', 'NASDAQ')
        ref_date: Data di riferimento
        days_needed: Numero di giorni di dati necessari (default 14)
    
    Returns:
        List di dict con {date, close} oppure None se fallisce
    """
    os.makedirs(PERPLEXITY_CACHE_DIR, exist_ok=True)
    
    # Controlla cache
    ref_date_str = pd.to_datetime(ref_date).strftime('%Y-%m-%d')
    cache_file = os.path.join(PERPLEXITY_CACHE_DIR, f'{index_name}_{ref_date_str}.json')
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                # Verifica che i dati non siano duplicati (problema qualità)
                if cached_data and len(cached_data) >= days_needed:
                    closes = [d['close'] for d in cached_data]
                    unique_closes = len(set(closes))
                    # Se più del 50% sono unici, usa cache
                    if unique_closes > len(closes) * 0.5:
                        return cached_data
                    else:
                        # Cache corrotta, elimina e riscarica
                        os.remove(cache_file)
        except:
            pass
    
    # Mappa nomi indici a nomi completi e ticker per Perplexity
    index_info = {
        "SP500": ("S&P 500", "^GSPC", "NYSE"),
        "NASDAQ": ("NASDAQ Composite", "^IXIC", "NASDAQ"), 
        "DAX": ("DAX 40", "^GDAXI", "XETRA Frankfurt"),
        "FTSE100": ("FTSE 100", "^FTSE", "London Stock Exchange"),
        "NIKKEI": ("Nikkei 225", "^N225", "Tokyo Stock Exchange")
    }
    
    info = index_info.get(index_name, (index_name, "", ""))
    index_full, ticker, exchange = info
    
    # Calcola range date
    end_date = pd.to_datetime(ref_date)
    start_date = end_date - pd.Timedelta(days=days_needed + 10)  # Buffer per weekend/festivi
    
    prompt = f"""Trova i prezzi di chiusura ESATTI e GIORNALIERI dell'indice {index_full} (ticker: {ticker}) dal {start_date.strftime('%d %B %Y')} al {end_date.strftime('%d %B %Y')}.

IMPORTANTE: Ogni giorno di trading DEVE avere un prezzo DIVERSO. I mercati si muovono ogni giorno.

Formato OBBLIGATORIO (una riga per giorno):
DATA: YYYY-MM-DD | CLOSE: prezzo_esatto

Regole:
1. Includi SOLO giorni di trading (escludi sabato, domenica, festivi)
2. Ogni prezzo deve essere UNICO e REALE (cercalo su fonti finanziarie)
3. Usa 2 decimali per i prezzi
4. Fornisci almeno {days_needed} giorni consecutivi di trading

Cerca i dati su Yahoo Finance, Google Finance, Bloomberg o Investing.com."""

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "Sei un terminale Bloomberg professionale. Fornisci SOLO dati finanziari verificati con precisione. MAI inventare o duplicare valori."
            },
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(PERPLEXITY_BASE_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        testo = data['choices'][0]['message']['content'].strip()
        
        # Parsing della risposta
        prices = []
        for line in testo.split('\n'):
            line = line.strip()
            if 'DATA:' in line.upper() and 'CLOSE:' in line.upper():
                try:
                    # Estrai data e prezzo con regex
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                    close_match = re.search(r'CLOSE:\s*([\d.,]+)', line, re.IGNORECASE)
                    
                    if date_match and close_match:
                        date_str = date_match.group(1)
                        close_str = close_match.group(1).replace(',', '')
                        close_val = float(close_str)
                        prices.append({'date': date_str, 'close': close_val})
                except:
                    continue
        
        if prices:
            # Ordina per data
            prices.sort(key=lambda x: x['date'])
            
            # Salva in cache
            with open(cache_file, 'w') as f:
                json.dump(prices, f)
            
            print(f"✓ Perplexity: recuperati {len(prices)} prezzi per {index_name}")
            return prices
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Errore connessione Perplexity API per {index_name}: {e}")
        return None
    except Exception as e:
        print(f"Errore Perplexity per {index_name}: {e}")
        return None


def fetch_future_close_yfinance(index_name, ref_date, days_ahead=7):
    """
    Recupera il prezzo di chiusura N giorni dopo ref_date usando yfinance.
    
    Args:
        index_name: Nome indice (es. 'SP500')
        ref_date: Data di riferimento (data della notizia)
        days_ahead: Giorni in avanti (default 7)
    
    Returns:
        Float con prezzo di chiusura a T+days_ahead, oppure None se non disponibile
    """
    tickers_map = {
        "SP500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DAX": "^GDAXI",
        "FTSE100": "^FTSE",
        "NIKKEI": "^N225"
    }
    
    if index_name not in tickers_map:
        return None
    
    ticker = tickers_map[index_name]
    ref_dt = pd.to_datetime(ref_date)
    
    # Cerca il prezzo tra T+days_ahead e T+days_ahead+5 (per gestire weekend/festivi)
    start_dt = ref_dt + pd.Timedelta(days=days_ahead)
    end_dt = ref_dt + pd.Timedelta(days=days_ahead + 10)
    
    try:
        df = yf.download(ticker, 
                        start=start_dt.strftime('%Y-%m-%d'),
                        end=end_dt.strftime('%Y-%m-%d'),
                        progress=False, auto_adjust=True)
        
        if not df.empty:
            # Gestione MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Prendi il primo giorno di trading disponibile dopo T+days_ahead
            return float(df['Close'].iloc[0])
    except Exception as e:
        print(f"Errore yfinance per {index_name} T+{days_ahead}: {e}")
    
    return None


def fetch_future_close_perplexity(index_name, ref_date, days_ahead=7):
    """
    Recupera il prezzo di chiusura N giorni dopo ref_date usando Perplexity API.
    Usato come fallback quando yfinance non ha dati.
    
    Args:
        index_name: Nome indice (es. 'SP500')
        ref_date: Data di riferimento
        days_ahead: Giorni in avanti (default 7)
    
    Returns:
        Float con prezzo di chiusura a T+days_ahead, oppure None se non disponibile
    """
    os.makedirs(PERPLEXITY_CACHE_DIR, exist_ok=True)
    
    ref_dt = pd.to_datetime(ref_date)
    target_date = ref_dt + pd.Timedelta(days=days_ahead)
    
    # Cache key per T+7
    cache_file = os.path.join(PERPLEXITY_CACHE_DIR, 
                              f'{index_name}_T7_{ref_dt.strftime("%Y-%m-%d")}.json')
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
                if cached.get('close'):
                    return cached['close']
        except:
            pass
    
    # Mappa indici
    index_info = {
        "SP500": ("S&P 500", "^GSPC"),
        "NASDAQ": ("NASDAQ Composite", "^IXIC"),
        "DAX": ("DAX 40", "^GDAXI"),
        "FTSE100": ("FTSE 100", "^FTSE"),
        "NIKKEI": ("Nikkei 225", "^N225")
    }
    
    info = index_info.get(index_name, (index_name, ""))
    index_full, ticker = info
    
    prompt = f"""Trova il prezzo di CHIUSURA ESATTO dell'indice {index_full} (ticker: {ticker}) 
per il giorno di trading più vicino a {target_date.strftime('%d %B %Y')} (circa 7 giorni dopo {ref_dt.strftime('%d %B %Y')}).

Se il {target_date.strftime('%d %B %Y')} è weekend o festivo, fornisci il prezzo del primo giorno di trading successivo.

FORMATO RISPOSTA (una sola riga):
DATA: YYYY-MM-DD | CLOSE: prezzo_esatto

Cerca il dato su Yahoo Finance, Google Finance, Bloomberg o Investing.com. Fornisci SOLO UN prezzo."""

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un terminale Bloomberg. Fornisci SOLO dati finanziari verificati."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(PERPLEXITY_BASE_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        testo = data['choices'][0]['message']['content'].strip()
        
        # Parsing
        for line in testo.split('\n'):
            line = line.strip()
            if 'CLOSE:' in line.upper():
                # Estrai prezzo
                match = re.search(r'CLOSE[:\s]+([0-9,\.]+)', line, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(',', '')
                    close_val = float(price_str)
                    
                    # Salva in cache
                    with open(cache_file, 'w') as f:
                        json.dump({'date': target_date.strftime('%Y-%m-%d'), 'close': close_val}, f)
                    
                    print(f"  ✓ Perplexity T+7: {index_name} = {close_val:.2f}")
                    return close_val
        
        return None
        
    except Exception as e:
        print(f"Errore Perplexity T+7 per {index_name}: {e}")
        return None


def get_close_t7(index_name, ref_date, days_ahead=7):
    """
    Ottiene il prezzo di chiusura a T+7 (7 giorni dopo la notizia).
    Prima prova yfinance, poi Perplexity come fallback.
    
    Args:
        index_name: Nome indice (es. 'SP500')
        ref_date: Data della notizia
        days_ahead: Giorni in avanti (default 7)
    
    Returns:
        Float con prezzo di chiusura, oppure np.nan se non disponibile
    """
    # Prima prova yfinance
    close_t7 = fetch_future_close_yfinance(index_name, ref_date, days_ahead)
    
    if close_t7 is not None:
        return close_t7
    
    # Fallback a Perplexity
    close_t7 = fetch_future_close_perplexity(index_name, ref_date, days_ahead)
    
    if close_t7 is not None:
        return close_t7
    
    return np.nan


def calc_addons_from_perplexity_data(prices, window=7):
    """
    Calcola momentum7, volatility7, drawdown e percentile7 dai dati Perplexity.
    
    Args:
        prices: Lista di dict {date, close} da Perplexity
        window: Finestra rolling (default 7)
    
    Returns:
        Dict con momentum7, volatility7, drawdown e percentile7 calcolati
    """
    result = {
        'momentum7': np.nan,
        'volatility7': np.nan,
        'drawdown': np.nan,
        'percentile7': np.nan
    }
    
    if not prices or len(prices) < 2:
        return result
    
    # Converti a DataFrame
    df = pd.DataFrame(prices)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    # Rimuovi eventuali NaN
    df = df.dropna(subset=['close'])
    
    if len(df) < 2:
        return result
    
    # Calcola momentum7: close attuale - close di 7 giorni fa
    if len(df) >= window + 1:
        result['momentum7'] = df['close'].iloc[-1] - df['close'].iloc[-(window + 1)]
    
    # Calcola volatility7: std dei rendimenti logaritmici
    if len(df) >= 2:
        df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
        if len(df) >= window:
            result['volatility7'] = df['log_ret'].tail(window).std(ddof=0)
        else:
            result['volatility7'] = df['log_ret'].dropna().std(ddof=0)
    
    # Calcola drawdown: (current - max_storico) / max_storico
    if len(df) >= 1:
        cummax = df['close'].expanding(min_periods=1).max()
        current_close = df['close'].iloc[-1]
        max_close = cummax.iloc[-1]
        if max_close > 0:
            result['drawdown'] = (current_close - max_close) / max_close
    
    # Calcola percentile7: posizione del valore corrente nella finestra
    if len(df) >= window:
        window_values = df['close'].tail(window).values
        current = window_values[-1]
        below = np.sum(window_values[:-1] < current)
        result['percentile7'] = below / (len(window_values) - 1) if len(window_values) > 1 else np.nan
    
    return result


def fill_missing_addons_with_perplexity(addons_dict, ref_date, index_name):
    """
    Completa gli add-ons mancanti (NaN) usando Perplexity API.
    
    Args:
        addons_dict: Dict con add-ons già calcolati (può contenere NaN)
        ref_date: Data di riferimento
        index_name: Nome indice (es. 'SP500')
    
    Returns:
        Dict aggiornato con valori recuperati da Perplexity
    """
    momentum_key = f'{index_name}_momentum7'
    volatility_key = f'{index_name}_volatility7'
    drawdown_key = f'{index_name}_drawdown'
    percentile_key = f'{index_name}_percentile7'
    
    # Controlla se servono dati da Perplexity
    need_momentum = momentum_key in addons_dict and pd.isna(addons_dict[momentum_key])
    need_volatility = volatility_key in addons_dict and pd.isna(addons_dict[volatility_key])
    need_drawdown = drawdown_key in addons_dict and pd.isna(addons_dict[drawdown_key])
    need_percentile = percentile_key in addons_dict and pd.isna(addons_dict[percentile_key])
    
    if not any([need_momentum, need_volatility, need_drawdown, need_percentile]):
        return addons_dict
    
    # Recupera dati da Perplexity
    prices = fetch_historical_prices_perplexity(index_name, ref_date, days_needed=14)
    
    if prices:
        perplexity_addons = calc_addons_from_perplexity_data(prices, window=7)
        
        if need_momentum and not pd.isna(perplexity_addons.get('momentum7')):
            addons_dict[momentum_key] = perplexity_addons['momentum7']
            print(f"  → {momentum_key} recuperato da Perplexity: {perplexity_addons['momentum7']:.2f}")
        
        if need_volatility and not pd.isna(perplexity_addons.get('volatility7')):
            addons_dict[volatility_key] = perplexity_addons['volatility7']
            print(f"  → {volatility_key} recuperato da Perplexity: {perplexity_addons['volatility7']:.6f}")
        
        if need_drawdown and not pd.isna(perplexity_addons.get('drawdown')):
            addons_dict[drawdown_key] = perplexity_addons['drawdown']
            print(f"  → {drawdown_key} recuperato da Perplexity: {perplexity_addons['drawdown']:.4f}")
        
        if need_percentile and not pd.isna(perplexity_addons.get('percentile7')):
            addons_dict[percentile_key] = perplexity_addons['percentile7']
            print(f"  → {percentile_key} recuperato da Perplexity: {perplexity_addons['percentile7']:.4f}")
    
    return addons_dict

# --- Fine sezione Perplexity ---

def calc_extra_addons_for_index(df_full, ref_date, index_name, tickers_map, window=7):
    """
    Calcola extra add-ons per un singolo indice usando dati storici reali.
    
    Args:
        df_full: DataFrame completo del database
        ref_date: Data di riferimento
        index_name: Nome indice (es. 'SP500')
        tickers_map: Dict {nome: ticker} (es. {'SP500': '^GSPC'})
        window: Finestra rolling (default 7)
    
    Returns:
        Dict con i 7 extra add-ons calcolati
    """
    result = {
        f'{index_name}_rolling_min7': np.nan,
        f'{index_name}_rolling_max7': np.nan,
        f'{index_name}_zscore7': np.nan,
        f'{index_name}_percentile7': np.nan,
        f'{index_name}_drawdown': np.nan,
        f'{index_name}_momentum7': np.nan,
        f'{index_name}_volatility7': np.nan
    }
    
    if index_name not in tickers_map:
        return result
    
    # Scarica dati storici
    hist_data = fetch_historical_batch([ref_date], {index_name: tickers_map[index_name]}, window=window+5)
    
    if index_name not in hist_data or hist_data[index_name].empty:
        return result
    
    # Estrai finestra
    window_df = get_window(hist_data[index_name], ref_date, window=window)
    
    if window_df.empty or 'Close' not in window_df.columns:
        return result
    
    # Calcola add-ons
    addons_df = calc_extra_addons(window_df)
    
    if not addons_df.empty:
        last_row = addons_df.iloc[-1]
        result[f'{index_name}_rolling_min7'] = last_row.get('rolling_min7', np.nan)
        result[f'{index_name}_rolling_max7'] = last_row.get('rolling_max7', np.nan)
        result[f'{index_name}_zscore7'] = last_row.get('zscore7', np.nan)
        result[f'{index_name}_percentile7'] = last_row.get('percentile7', np.nan)
        result[f'{index_name}_drawdown'] = last_row.get('drawdown', np.nan)
        result[f'{index_name}_momentum7'] = last_row.get('momentum7', np.nan)
        result[f'{index_name}_volatility7'] = last_row.get('volatility7', np.nan)
    
    return result

def calc_all_extra_addons(ref_date, window=7, use_perplexity_fallback=True):
    """
    Calcola tutti gli extra add-ons per tutti gli indici per una data specifica.
    Se yfinance non fornisce dati sufficienti, usa Perplexity come fallback.
    
    Args:
        ref_date: Data di riferimento
        window: Finestra rolling (default 7)
        use_perplexity_fallback: Se True, usa Perplexity per dati mancanti (default True)
    
    Returns:
        Dict con tutti i 35 extra add-ons (7 per ogni indice)
    """
    tickers_map = {
        "SP500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DAX": "^GDAXI",
        "FTSE100": "^FTSE",
        "NIKKEI": "^N225"
    }
    
    all_addons = {}
    
    # Scarica tutti i dati storici in batch per efficienza
    # Usa 30 giorni di buffer per garantire 14+ trading days
    hist_data = fetch_historical_batch([ref_date], tickers_map, window=30)
    
    for index_name in tickers_map.keys():
        if index_name not in hist_data or hist_data[index_name].empty:
            # Imposta NaN per tutti gli add-ons di questo indice
            for addon in ['rolling_min7', 'rolling_max7', 'zscore7', 'percentile7', 
                         'drawdown', 'momentum7', 'volatility7']:
                all_addons[f'{index_name}_{addon}'] = np.nan
            continue
        
        # Estrai finestra - prendi 14 trading days per momentum7
        window_df = get_window(hist_data[index_name], ref_date, window=14)
        
        if window_df.empty or 'Close' not in window_df.columns:
            for addon in ['rolling_min7', 'rolling_max7', 'zscore7', 'percentile7', 
                         'drawdown', 'momentum7', 'volatility7']:
                all_addons[f'{index_name}_{addon}'] = np.nan
            continue
        
        # Calcola add-ons
        addons_df = calc_extra_addons(window_df)
        
        if not addons_df.empty:
            last_row = addons_df.iloc[-1]
            all_addons[f'{index_name}_rolling_min7'] = last_row.get('rolling_min7', np.nan)
            all_addons[f'{index_name}_rolling_max7'] = last_row.get('rolling_max7', np.nan)
            all_addons[f'{index_name}_zscore7'] = last_row.get('zscore7', np.nan)
            all_addons[f'{index_name}_percentile7'] = last_row.get('percentile7', np.nan)
            all_addons[f'{index_name}_drawdown'] = last_row.get('drawdown', np.nan)
            all_addons[f'{index_name}_momentum7'] = last_row.get('momentum7', np.nan)
            all_addons[f'{index_name}_volatility7'] = last_row.get('volatility7', np.nan)
        else:
            for addon in ['rolling_min7', 'rolling_max7', 'zscore7', 'percentile7', 
                         'drawdown', 'momentum7', 'volatility7']:
                all_addons[f'{index_name}_{addon}'] = np.nan
    
    # --- Fallback Perplexity per valori mancanti ---
    if use_perplexity_fallback:
        for index_name in tickers_map.keys():
            all_addons = fill_missing_addons_with_perplexity(all_addons, ref_date, index_name)
    
    return all_addons

# Funzione per calcolare gli extra add-ons (successivi 6 add-ons della lista, dal settimo al dodicesimo) da una riga del DataFrame