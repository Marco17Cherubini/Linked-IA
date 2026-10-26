import os # libreria per operazioni sul sistema operativo, dato che operiamo nella creazione di file e cartelle
import pandas as pd # libreria per la manipolazione dei dati, consente di lavorare con DataFrame

# Configurazione indici e add-ons
INDICI = ["SP500", "NASDAQ", "DAX", "FTSE100", "NIKKEI"]
CORE_ADDONS = ["gap_ret", "intra_ret", "range_pct", "tr", "atr7", "rv7", "rs_vol7"]
EXTRA_ADDONS = ["rolling_min7", "rolling_max7", "zscore7", "percentile7", "drawdown", "momentum7", "volatility7"]

def get_database_dir(): # recupera il percorso della directory del database, è la parte di script che si occupa di gestire il database in Excel
    base = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(base, "database")
    return db_dir
def crea_database_se_necessario(filename="database.xlsx"): # crea il file Excel del database se non esiste
    directory = get_database_dir()
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    xlsx_path = os.path.join(directory, filename) # percorso completo del file Excel
    if not os.path.exists(xlsx_path): # se il file non esiste, crealo con le colonne necessarie
        # Definisci le colonne del DataFrame
        ohlcv = ["Open", "High", "Low", "Close", "Volume"]
        columns = ["Data", "Titolo", "Corpo", "Fonti", "report_nesso"] # colonne base per notizie
        for idx in INDICI:
            for o in ohlcv:
                columns.append(f"{idx}_{o}")
            columns.append(f"{idx}_Close_prev")
            for a in CORE_ADDONS:
                columns.append(f"{idx}_{a}")
            for a in EXTRA_ADDONS:
                columns.append(f"{idx}_{a}")
        df = pd.DataFrame(columns=columns)
        df.to_excel(xlsx_path, index=False)
    return xlsx_path

# è la parte di script che crea il database nel momento in cui manca, con le colonne necessarie per memorizzare notizie e dati OHLCV + add-ons