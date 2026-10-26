import pandas_market_calendars as mcal #per i calendari di mercato
import pandas as pd #consente il lavoro con DataFrame
import yfinance as yf #per scaricare dati finanziari da Yahoo Finance

def get_close_prev(date_str, calendar_code, ticker=None, df_prices=None): # restituisce la chiusura del trading day precedente a 'date_str' per il ticker indicato
    """
    Restituisce la chiusura del trading day precedente a 'date_str' per il ticker indicato.
    Se df_prices è fornito, cerca prima lì. Se non trova il dato, scarica solo il giorno mancante da yfinance.
    df_prices deve avere una colonna 'Date' (datetime) e 'Close'.
    """
    data_dt = pd.Timestamp(date_str) # Converti a Timestamp
    cal = mcal.get_calendar(calendar_code) # Ottieni il calendario di mercato
    valid_days = cal.valid_days(start_date=data_dt - pd.Timedelta(days=30), end_date=data_dt) # Ottieni i giorni di trading negli ultimi 30 giorni
    valid_days = valid_days.tz_localize(None) # Rimuovi la timezone per confronto
    prev_days = valid_days[valid_days < data_dt] # Filtra i giorni precedenti a data_dt
    if len(prev_days) == 0: 
        return None
    prev_day = prev_days[-1]
    # Se df_prices è fornito, cerca prima lì
    if df_prices is not None:
        row = df_prices[df_prices["Date"] == prev_day]
        if not row.empty:
            return float(row.iloc[0]["Close"])
    # Se non trovato o df_prices non fornito, scarica solo il giorno mancante
    if ticker is not None:
        start = prev_day.strftime('%Y-%m-%d')
        end = (prev_day + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        prezzi = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False
        )
        if not prezzi.empty: # Se non trovato o df_prices non fornito, scarica solo il giorno mancante
            first_date = prezzi.index[0].date()
            if first_date == prev_day.date():
                return float(prezzi['Close'].iloc[0])
    return None

# Questa funzione è cruciale per calcolare il prezzo di chiusura del giorno di trading precedente, necessario per calcolare vari indicatori finanziari (add-ons) che dipendono dal prezzo di chiusura del giorno precedente.
# Risulta essere una delle funzioni fondamentali del prototipo, in quanto consente di calcolare gli add-ons.