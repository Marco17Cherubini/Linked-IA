import pandas as pd # libreria per la manipolazione dei dati, consente di lavorare con DataFrame
import numpy as np # libreria per il calcolo scientifico, utile per operazioni numeriche avanzate
import os # libreria per interagire con il sistema operativo, utile per operazioni su file e directory
import pickle  # libreria per la serializzazione e deserializzazione di oggetti Python, utile per caching
import warnings # libreria per gestire avvisi e messaggi di warning
import yfinance as yf # libreria per scaricare dati finanziari da Yahoo Finance
from core_addons import calc_core_addons_from_row # recupera funzioni da core_addons.py
from extra_addons import calc_extra_addons, calc_all_extra_addons, fetch_historical_batch, get_window, get_close_t7, calc_momentum_forward # recupera funzioni da extra_addons.py
from close_prev import get_close_prev # recupera funzioni da close_prev.py

warnings.simplefilter(action='ignore', category=FutureWarning) # ignora avvisi di tipo FutureWarning per pulizia output

# --- Funzioni di utilità per dati OHLCV ---
def get_ohlcv_for_dates(dates, ticker, window=20, cache_dir='ohlcv_cache'): # recupera dati OHLCV per date specifiche con caching
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f'{ticker}_ohlcv.pkl')
    if os.path.exists(cache_file): # carica cache se esiste
        with open(cache_file, 'rb') as f:
            cache = pickle.load(f)
    else: 
        cache = {}
    new_dates = [d for d in dates if d not in cache]
    for d in new_dates: # scarica dati per nuove date
        try: 
            start = pd.to_datetime(d) - pd.Timedelta(days=window)
            end = pd.to_datetime(d) + pd.Timedelta(days=window)
            df = yf.download(ticker, start=start.strftime('%Y-%m-%d'), end=(end+pd.Timedelta(days=1)).strftime('%Y-%m-%d'), progress=False)
            cache[d] = df
        except Exception as e:
            cache[d] = None
    with open(cache_file, 'wb') as f: 
        pickle.dump(cache, f)
    return cache

INDICI_INFO = {
    "SP500": ("XNYS", "^GSPC"),
    "NASDAQ": ("XNYS", "^IXIC"),
    "DAX": ("XFRA", "^GDAXI"),
    "FTSE100": ("XLON", "^FTSE"),
    "NIKKEI": ("XTKS", "^N225")
}

TICKERS_MAP = {
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "FTSE100": "^FTSE",
    "NIKKEI": "^N225"
}

# --- Funzione di orchestrazione per riempire una riga ---
def fill_row(row, df=None, idx=None, hist_cache=None):
    """
    Riempie una riga con core e extra add-ons.
    
    Args:
        row: Riga del DataFrame
        df: DataFrame completo (per core add-ons rolling)
        idx: Indice della riga nel DataFrame
        hist_cache: Cache di dati storici pre-scaricati (opzionale, per performance)
    """
    data = row.get('Data')
    
    # La colonna Close_prev deve essere già presente nel DataFrame, calcolata in batch
    # (nessuna chiamata a get_close_prev qui)
    
    # Calcola core add-ons
    core_addons = calc_core_addons_from_row(row, df=df, idx=idx)
    for k, v in core_addons.items():
        row[k] = v
    
    # Calcola extra add-ons usando dati storici reali
    if data:
        try:
            # Se abbiamo cache pre-scaricata, usala
            if hist_cache:
                for index in INDICI_INFO.keys():
                    if index in hist_cache and not hist_cache[index].empty:
                        window_df = get_window(hist_cache[index], data, window=15)  # 15 giorni per calcoli rolling
                        if not window_df.empty and 'Close' in window_df.columns:
                            extra = calc_extra_addons(window_df)
                            if not extra.empty:
                                last_row = extra.iloc[-1]
                                # Assegna add-ons standard
                                for col in ['rolling_min7','rolling_max7','zscore7','percentile7','drawdown','volatility7']:
                                    row[f"{index}_{col}"] = last_row.get(col, np.nan)
                                
                                # Calcola momentum7 FORWARD: Close[T+7] - Close[T]
                                close_t = row.get(f"{index}_Close", np.nan)
                                close_t7 = get_close_t7(index, data, days_ahead=7)
                                row[f"{index}_momentum7"] = calc_momentum_forward(close_t, close_t7)
                            else:
                                for col in ['rolling_min7','rolling_max7','zscore7','percentile7','drawdown','momentum7','volatility7']:
                                    row[f"{index}_{col}"] = np.nan
                        else:
                            for col in ['rolling_min7','rolling_max7','zscore7','percentile7','drawdown','momentum7','volatility7']:
                                row[f"{index}_{col}"] = np.nan
                    else:
                        for col in ['rolling_min7','rolling_max7','zscore7','percentile7','drawdown','momentum7','volatility7']:
                            row[f"{index}_{col}"] = np.nan
            else:
                # Scarica dati storici on-demand
                extra_addons = calc_all_extra_addons(data, window=7)
                for k, v in extra_addons.items():
                    # Per momentum7, ricalcola come forward
                    if 'momentum7' in k:
                        index = k.replace('_momentum7', '')
                        close_t = row.get(f"{index}_Close", np.nan)
                        close_t7 = get_close_t7(index, data, days_ahead=7)
                        row[k] = calc_momentum_forward(close_t, close_t7)
                    else:
                        row[k] = v
        except Exception as e:
            print(f"Errore calcolo extra add-ons per {data}: {e}")
            for index in INDICI_INFO.keys():
                for col in ['rolling_min7','rolling_max7','zscore7','percentile7','drawdown','momentum7','volatility7']:
                    row[f"{index}_{col}"] = np.nan
    
    return row

# --- Funzione per riempire l'intero DataFrame ---
def fill_dataframe(df):
    """
    Riempie l'intero DataFrame con core e extra add-ons.
    Scarica dati storici in batch per efficienza.
    """
    df = df.copy()
    
    # Raccogli tutte le date uniche
    dates = df['Data'].dropna().unique().tolist()
    
    if dates:
        # Pre-scarica tutti i dati storici in batch
        print(f"Scaricamento dati storici per {len(dates)} date...")
        hist_cache = fetch_historical_batch(dates, TICKERS_MAP, window=15)
        print("Download completato.")
    else:
        hist_cache = {}
    
    # Riempi ogni riga
    for idx, row in df.iterrows():
        df.loc[idx] = fill_row(row, df=df, idx=idx, hist_cache=hist_cache)
    
    return df

if __name__ == "__main__":
    df = pd.read_excel('database/database.xlsx')
    df_filled = fill_dataframe(df)
    df_filled.to_excel('database/database.xlsx', index=False)
    print("Filling completato. Output salvato in database.xlsx")