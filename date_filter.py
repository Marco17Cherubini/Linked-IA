import pandas as pd #consente il lavoro con DataFrame
import pandas_market_calendars as mcal #per i calendari di mercato
import yfinance as yf #per scaricare dati finanziari da Yahoo Finance

def get_trading_window(date_base, ticker, calendar_code, days=20): #per gli ultimi 20 giorni di trading restituisce i prezzi, funziona parzialmente inutile, da rivedere in fase di rielaborazione prototipo
    """
    Restituisce un DataFrame con tutti i trading days e prezzi degli ultimi 'days' giorni fino a date_base (incluso).
    """
    date_base = pd.to_datetime(date_base)
    start_date = date_base - pd.DateOffset(days=days)
    end_date = date_base
    # Ottieni tutti i trading days nella finestra
    cal = mcal.get_calendar(calendar_code)
    trading_days = cal.valid_days(start_date=start_date, end_date=end_date).tz_localize(None)
    # Scarica i prezzi per la finestra
    prezzi = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=(end_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), auto_adjust=True, progress=False)
    prezzi = prezzi.reset_index()
    prezzi['Date'] = pd.to_datetime(prezzi['Date'])
    # Filtra solo i trading days
    prezzi_window = prezzi[prezzi['Date'].isin(trading_days)]
    return prezzi_window  # DataFrame con Date, Open, High, Low, Close, Volume

def get_trading_days(date_filter, market="XNYS", window_days=7): # restituisce i trading days negli ultimi window_days rispetto a date_filter, -7gg rispetto a date_filter
    """
    Restituisce i trading days negli ultimi window_days rispetto a date_filter.
    """
    cal = mcal.get_calendar(market)
    data_dt = pd.Timestamp(date_filter)
    valid_days = cal.valid_days(start_date=data_dt - pd.Timedelta(days=window_days), end_date=data_dt)
    return valid_days.tz_localize(None)

def get_last_trading_day(date_filter, market="XNYS", window_days=7): # restituisce l'ultimo trading day prima o uguale a date_filter
    """
    Restituisce l'ultimo trading day prima o uguale a date_filter.
    """
    valid_days = get_trading_days(date_filter, market, window_days)
    if len(valid_days) > 0:
        return valid_days[-1]
    return None

def get_next_trading_day(date_filter, market="XNYS", window_days=10):
    """
    Restituisce il primo trading day DOPO date_filter.
    Utile per calcolare dati T+1 (giorno successivo alla notizia).
    """
    cal = mcal.get_calendar(market)
    data_dt = pd.Timestamp(date_filter)
    # Cerca nei prossimi window_days
    valid_days = cal.valid_days(
        start_date=data_dt + pd.Timedelta(days=1),  # Escludi data_filter
        end_date=data_dt + pd.Timedelta(days=window_days)
    )
    valid_days = valid_days.tz_localize(None)
    if len(valid_days) > 0:
        return valid_days[0]  # Primo giorno di trading successivo
    return None

def get_rolling_window(date_filter, window=7): # restituisce la finestra temporale per rolling (inizio, fine) su cui si basano get_trading_days e get_last_trading_day
    """
    Restituisce la finestra temporale per rolling (inizio, fine).
    """
    date_base = pd.to_datetime(date_filter)
    start = date_base - pd.Timedelta(days=window)
    end = date_base + pd.Timedelta(days=window)
    return start, end

# è una delle funzioni più importanti del prototipo, consente di filtrare i dati in base alla data di interesse e al calendario di mercato. E' stata progettata a parte per essere facilmente ottimizzabile in caso di errori.