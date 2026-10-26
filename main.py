from fetcher import fetch_rss_news, print_prezzi_articolo # recupera funzioni da fetcher.py
from scraper import scrape_articles # recupera funzioni da scraper.py
from new_store_articles2 import store_articles # recupera funzioni da new_store_articles2.py
from archive_manager import selezione_intelligente # recupera funzioni da archive_manager.py
from deepseek_manager import run_lia_deepseek # sistema analisi pattern con DeepSeek AI
from imf_validator import run_imf_validation # validazione con metriche IMF
import pandas as pd # libreria per la manipolazione dei dati, consente di lavorare con DataFrame


def main(): # cuore del progetto, funzione principale, in fondo spiegato funzionamento programma
    date_filter = input("Inserisci la data (YYYY-MM-DD): ") # input data per filtrare notizie
    df_links = fetch_rss_news({ # raccolta di link per scaricare notizie, sarebbe ottimizzabile inserendo fonti a pagamento e di enorme rilievo come Bloomberg, FT, WSJ, ecc.
        "Reuters": "https://feeds.reuters.com/reuters/topNews",
        "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "Investing": "https://www.investing.com/rss/news_25.rss"
    }, date_filter)

    if not df_links.empty: # se df_links non è vuoto, procedi con scraping e salvataggio
        print("\nNotizie trovate nei feed RSS:")
        for idx, row in df_links.iterrows():
            print(f"Fonte: {row['Fonte']}")
            print(f"Titolo: {row['Titolo']}")
            print(f"Link: {row['Link']}")
            print(f"Data: {row['Data']}\n")

        dettagli = scrape_articles(df_links) # esegue scraping degli articoli
        print(f"Numero di articoli da salvare: {len(dettagli)}")
        # Forza il salvataggio di tutti gli articoli trovati
        if len(dettagli) > 0:
            store_articles(dettagli)
            print(f"\nArticoli salvati nel database per la data {date_filter}.")
        else:
            print("Nessun dettaglio da salvare dopo scraping.")
    else: # se df_links è vuoto, attiva selezione intelligente, ottimizzabile con implementazione di database come Factiva, Pinecone, ecc. tutti a pagamento
        print("\nNessuna notizia trovata nei feed RSS per la data inserita.")
        print("Attivo la selezione intelligente...") # selezione intelligente per cercare notizie rilevanti in archivio utilizzando ChatGPT per fornire prototipo di come funziona l'intero script
        articoli = selezione_intelligente(date_filter) # cerca notizie rilevanti nell'archivio tramite date_filter
        dettagli = []
        if articoli: # se articoli non è vuoto, procedi con salvataggio
            dettagli = []
            for articolo in articoli:
                print(f"Data: {articolo['data']}")
                print(f"Titolo: {articolo['titolo']}")
                if articolo.get('fonti'):
                    print("Fonti:")
                    for fonte in articolo['fonti']:
                        print(f"  - {fonte}")
                print()
                dettagli.append({
                    "Fonte": "Perplexity",
                    "Titolo": articolo["titolo"],
                    "Corpo": articolo["corpo"],
                    "Data": articolo["data"],
                    "Fonti": "; ".join(articolo.get("fonti", []))
                })
            store_articles(dettagli) # salva articoli trovati
            print(f"\nArticoli salvati nel database per l'intervallo {articoli[0]['data']} - {articoli[-1]['data']}.") 
            # Stampa prezzi accoppiati alle notizie
            for articolo in dettagli:
                print_prezzi_articolo(articolo)
            costo_totale = len(articoli) * 0.0005
            print(f"Totale stimato speso per ricerca intelligente: ${costo_totale:.4f}")
        else:
            print("Nessun evento trovato.")
            return  # Esce se nessun evento trovato
    
    # LiA Analysis: analisi basata su DeepSeek per pattern matching
    # store_articles già chiamato sopra, qui usiamo i risultati
    if dettagli:
        print("\n--- ANALISI LiA DeepSeek (Pattern Matching + AI) ---")
        # Ricarica il database per ottenere i report_nesso aggiornati
        from db_manager import crea_database_se_necessario
        xlsx_path = crea_database_se_necessario()
        df_db = pd.read_excel(xlsx_path)
        # Prepara lista di report_nesso per LiA DeepSeek
        report_nesso_list = []
        for art in dettagli:
            titolo = art.get("Titolo", "")
            mask = df_db["Titolo"] == titolo
            if mask.any():
                report = df_db.loc[mask, "report_nesso"].iloc[0]
                if pd.notna(report) and report:
                    report_nesso_list.append({
                        "Titolo": titolo,
                        "Data": art.get("Data", ""),
                        "report_nesso": str(report)
                    })
        if report_nesso_list:
            # Step 1: Analisi pattern con DeepSeek
            risultati_lia = run_lia_deepseek(report_nesso_list)
            
            # Step 2: Validazione IMF - Controllo incrociato con metriche Fondo Monetario Internazionale
            if risultati_lia:
                run_imf_validation(risultati_lia)

if __name__ == "__main__":
    main()

def print_notizia_e_prezzi(row):
    # Stampa dettagliata: data, titolo, corpo, fonti, prezzi OHLCV e add-ons
    print(f"Data: {row.get('Data')}")
    print(f"Titolo: {row.get('Titolo')}")
    print(f"Corpo: {row.get('Corpo')}")
    print(f"Fonti: {row.get('Fonti')}")
    # Add-ons esistenti: core (gap_ret, intra_ret, range_pct, tr, atr7, rv7, rs_vol7)
    # e extra (rolling_min7, rolling_max7, zscore7, percentile7, drawdown, momentum7, volatility7)
    for key in row.keys():
        if any(x in key for x in ['Open', 'High', 'Low', 'Close', 'Volume', 'Close_prev', 
               'gap_ret', 'intra_ret', 'range_pct', 'tr', 'atr7', 'rv7', 'rs_vol7',
               'rolling_min7', 'rolling_max7', 'zscore7', 'percentile7', 'drawdown', 'momentum7', 'volatility7']):
            print(f"{key}: {row[key]}")
    print("-" * 60)

# modulo centrale, importa da tutti gli altri e avvia tutto tramite main(), rappresenta il cuore del prototipo LiA il cui obiettivo è collegare notizie e prezzi di mercato in maniera da costruire una mappa di supporto alle decisioni intelligente.