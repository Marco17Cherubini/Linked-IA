import pandas as pd # importa la libreria pandas
import yfinance as yf # importa yahoo finance per scaricare i dati di mercato
from main_filler import fill_dataframe # importa la funzione fill_dataframe dal modulo main_filler per riempire i dati mancanti nel dataframe
from close_prev import get_close_prev # importa la funzione get_close_prev dal modulo close_prev per ottenere il prezzo di chiusura precedente
from db_manager import crea_database_se_necessario # importa la funzione crea_database_se_necessario dal modulo db_manager per poter operare sul database
from date_filter import get_last_trading_day # importa la funzione get_last_trading_day dal modulo date_filter per ottenere l'ultimo giorno di trading
from deepseek_manager import run_analysis_deepseek # importa DeepSeek per analisi pattern (sostituisce GPT)

# Configurazione indici
INDICI = {
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "FTSE100": "^FTSE",
    "NIKKEI": "^N225"
}

CALENDARI = {
    "SP500": "XNYS",
    "NASDAQ": "XNYS",
    "DAX": "XFRA",
    "FTSE100": "XLON",
    "NIKKEI": "XTKS"
}

def store_articles(dettagli): # funzione principale per elaborare e salvare gli articoli
    articoli_puliti = [] # lista per memorizzare gli articoli puliti
    if dettagli: # se dettagli non è vuoto
        for articolo in dettagli: # per ogni articolo in dettagli
            titolo = str(articolo.get("Titolo") or articolo.get("titolo") or "").strip() # recupera e salva il titolo dell'articolo se dettagli non è vuoto
            corpo = str(articolo.get("Corpo") or articolo.get("corpo") or "").strip().replace("\n", " ").replace("  ", " ") # recupera e salva il corpo dell'articolo, rimuovendo nuove righe e spazi doppi, se dettagli non è vuoto
            fonti = str(articolo.get("Fonti") or articolo.get("fonti") or "").strip() # recupera e salva le fonti dell'articolo se dettagli non è vuoto
            data = articolo.get("Data") or articolo.get("data") or "" # recupera e salva la data dell'articolo se dettagli non è vuoto
            if not titolo and not corpo: # se sia il titolo che il corpo sono vuoti, salta all'articolo successivo segnando solo la data
                continue 
            articoli_puliti.append({ 
                "Data": data,
                "Titolo": titolo,
                "Corpo": corpo,
                "Fonti": fonti
            })
    if not articoli_puliti: # se articoli_puliti è vuoto, stampa un messaggio di avviso e termina la funzione
        print("Nessun articolo valido da elaborare.")
        return [], []

    # Crea (se necessario) e ottieni il path del database all'inizio
    xlsx_path = crea_database_se_necessario() 

    for articolo in articoli_puliti: # per ogni articolo in articoli_puliti, recupera e salva i prezzi di mercato per ogni indice
        data = articolo.get("Data") or articolo.get("data") 
        if not data: 
            continue
        for nome, ticker in INDICI.items(): # per ogni indice in INDICI va a recuperare i prezzi di riferimento e li salva nel database tramite il recupero dell'ultimo trading day utile, con una finestra di 7 giorni
            market = CALENDARI[nome]
            articolo[f"{nome}_Close_prev"] = get_close_prev(data, market, ticker) # recupera e salva il prezzo di chiusura precedente, importando la data di riferimento, il mercato e il ticker
            last_trading_day = get_last_trading_day(data, market, window_days=7) # finestra di 7 giorni per trovare l'ultimo trading day
            if last_trading_day is None:
                articolo[f"{nome}_Open"] = "" # salva l'open come stringa vuota se non trova l'ultimo trading day
                articolo[f"{nome}_High"] = "" # salva l'high come stringa vuota se non trova l'ultimo trading day
                articolo[f"{nome}_Low"] = "" # salva il low come stringa vuota se non trova l'ultimo trading day
                articolo[f"{nome}_Close"] = "" # salva il close come stringa vuota se non trova l'ultimo trading day
                articolo[f"{nome}_Volume"] = "" # salva il volume come stringa vuota se non trova l'ultimo trading day
                continue
            try: # prova a scaricare i dati di mercato per l'ultimo trading day e salvarli nel database, quando trova il trading day
                start_str = last_trading_day.strftime('%Y-%m-%d') # formatta la data in stringa
                end_dt = last_trading_day + pd.Timedelta(days=1) # aggiunge un giorno alla data per coprire l'intera giornata
                 # scarica i dati di mercato da Yahoo Finance
                prezzi = yf.download(ticker, start=start_str, end=end_dt.strftime("%Y-%m-%d"), auto_adjust=True, progress=False)
                if not prezzi.empty: # se i dati non sono vuoti, salva i prezzi nel database
                    articolo[f"{nome}_Open"] = float(prezzi["Open"].iloc[0])
                    articolo[f"{nome}_High"] = float(prezzi["High"].iloc[0])
                    articolo[f"{nome}_Low"] = float(prezzi["Low"].iloc[0])
                    articolo[f"{nome}_Close"] = float(prezzi["Close"].iloc[0])
                    articolo[f"{nome}_Volume"] = float(prezzi["Volume"].iloc[0])
                else:
                    articolo[f"{nome}_Open"] = ""
                    articolo[f"{nome}_High"] = ""
                    articolo[f"{nome}_Low"] = ""
                    articolo[f"{nome}_Close"] = ""
                    articolo[f"{nome}_Volume"] = ""
            except Exception as e: # in caso di errore, stampa l'errore e salva i prezzi come stringhe vuote
                articolo[f"{nome}_Open"] = ""
                articolo[f"{nome}_High"] = ""
                articolo[f"{nome}_Low"] = ""
                articolo[f"{nome}_Close"] = ""
                articolo[f"{nome}_Volume"] = ""
    colonne_base = list(pd.DataFrame(articoli_puliti).columns) # crea una lista delle colonne base presenti in articoli_puliti
    for articolo in articoli_puliti: # per ogni articolo in articoli_puliti, assicura che tutte le colonne base siano presenti, aggiungendo None se mancano
        for col in colonne_base:
            if col not in articolo or articolo[col] == "":
                articolo[col] = None
    df_new = pd.DataFrame(articoli_puliti) # crea un dataframe pandas da articoli_puliti
    df_new = df_new[colonne_base] # riordina le colonne del dataframe secondo colonne_base

    # --- Gestione database: crea se necessario, salva i dati ---
    xlsx_path = crea_database_se_necessario()
    try:
        df_existing = pd.read_excel(xlsx_path)
    except FileNotFoundError:
        # Se il file non esiste, crealo con le colonne di df_new
        df_existing = pd.DataFrame(columns=df_new.columns)
        df_existing.to_excel(xlsx_path, index=False)
    # Allinea le colonne
    for col in df_existing.columns:
        if col not in df_new.columns:
            df_new[col] = None
    for col in df_new.columns:
        if col not in df_existing.columns:
            df_existing[col] = None
    df_new = df_new[df_existing.columns]
    # Unisci, rimuovi duplicati, riempi e salva
    df_all = pd.concat([df_existing, df_new], ignore_index=True)
    df_all = df_all.drop_duplicates(subset=["Data", "Titolo", "Corpo"])
    df_filled = fill_dataframe(df_all)
    df_filled.to_excel(xlsx_path, index=False)
    print(f"✅ Articoli elaborati e salvati su {xlsx_path}")

    # Filtro robusto: prendi solo gli articoli nuovi (Data+Titolo)
    chiavi_nuovi = set((str(art.get("Data")), str(art.get("Titolo") or art.get("titolo") or "").strip()) for art in dettagli)
    articoli_completi = [
        r for r in df_filled.to_dict(orient="records")
        if (str(r.get("Data")), str(r.get("Titolo") or "").strip()) in chiavi_nuovi
    ]
    print(f"Articoli nuovi da analizzare/salvare: {len(articoli_completi)}")
    for articolo in articoli_completi: 
        articolo["prezzi"] = {
            k: articolo[k] for k in articolo
            if any(x in k for x in ["Open", "High", "Low", "Close", "Volume"])
            and "_T1" not in k  # escludi colonne T1
        }
        articolo["addons"] = {
            k: articolo[k] for k in articolo
            if k not in articolo["prezzi"]
            and k not in ["Titolo", "Corpo", "Fonti", "Data", "report", "report_nesso"]
            and "_T1" not in k  # escludi colonne T1
            and (isinstance(articolo[k], (int, float)) or (isinstance(articolo[k], str) and articolo[k].replace('.', '', 1).isdigit()))
        }
    if not articoli_completi:
        print("Nessun nuovo articolo da analizzare/salvare.")
        return [], []

    report_nesso_list = run_analysis_deepseek(articoli_completi)  # usa DeepSeek per analisi pattern
    # Aggiorna la colonna report_nesso nel database
    df = pd.read_excel(xlsx_path)
    if report_nesso_list and isinstance(report_nesso_list[0], dict):
        for report in report_nesso_list:
            mask = (df["Titolo"] == report["Titolo"]) & (df["Data"] == report["Data"])
            df.loc[mask, "report_nesso"] = report["report_nesso"]
    else:
        # fallback: se report_nesso_list è una lista semplice, la assegna in ordine
        df["report_nesso"] = report_nesso_list
    df.to_excel(xlsx_path, index=False)
    print("Colonna 'report_nesso' aggiornata e salvata nel database.")
    # Ritorna sia i dati completi che i report
    return articoli_completi, report_nesso_list 

# l'obiettivo di new_store_articles2.py è di elaborare e salvare articoli in un database Excel, arricchendoli con dati di mercato e analisi del contenuto. Ogni funzione di salvataggio e di arricchimento dati è in mano a questo script
