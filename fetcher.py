import feedparser # per parsing feed RSS
import pandas as pd # libreria per la manipolazione dei dati, consente di lavorare con DataFrame

def fetch_rss_news(rss_feeds, date_filter): # recupera notizie da feed RSS per una data specifica, prompt di selezione sottostante
    """
    Ritorna un DataFrame con le notizie RSS per la data richiesta.
    Se il DataFrame è vuoto, la selezione intelligente (GPT) verrà gestita dal main.
    """
    news_data = [] # lista per memorizzare notizie trovate
    for source, url in rss_feeds.items(): 
        try: # si recupera data per i 10 valori presenti (YYYY-MM-DD) e si avvia il fetch delle notizie (vengono mandate a schermo)
            feed = feedparser.parse(url) 
            for entry in feed.entries: 
                entry_date_raw = entry.get('published', entry.get('updated', ''))
                try:
                    entry_date = entry_date_raw[:10]
                except Exception:
                    entry_date = ""
                if entry_date == date_filter:
                    news_data.append({
                        "Fonte": source,
                        "Titolo": entry.title,
                        "Sintesi": entry.get('summary', ''),
                        "Link": entry.link,
                        "Data": entry_date
                    })
        except Exception as e: # se presenti errori, stampa errore e continua
            print(f"Errore nel feed {source}: {e}")

    df = pd.DataFrame(news_data)
    return df

def print_prezzi_articolo(articolo): # promptato per stampare i prezzi Close associati alle notizie
    """Stampa a schermo i prezzi di chiusura degli indici per un articolo, se presenti."""
    indici = [
        "SP500_Close", "NASDAQ_Close", "DAX_Close", "FTSE100_Close", "NIKKEI_Close"
    ]
    print(f"Data: {articolo.get('Data', '')} | Titolo: {articolo.get('Titolo', '')}") # stampa data e titolo
    for idx in indici: # per ogni indice, stampa il prezzo di chiusura se presente
        prezzo = articolo.get(idx, None)
        if prezzo not in (None, ""):
            print(f"  {idx.replace('_Close','')}: {prezzo}")
    print()

def print_notizia_e_prezzi(articolo): # promptato per stampare tutti i dati OHLCV + add-ons per ogni indice
    """Stampa la notizia (titolo, sintesi, fonte, data) e TUTTI i dati OHLCV + add-ons per ogni indice."""
    print(f"Data: {articolo.get('Data', '')}")
    print(f"Titolo: {articolo.get('Titolo', '')}")
    if articolo.get('Sintesi'): 
        print(f"Sintesi: {articolo.get('Sintesi')}")
    print(f"Fonte: {articolo.get('Fonte', '')}")
    print(f"Link: {articolo.get('Link', '')}")
    indici = ["SP500", "NASDAQ", "DAX", "FTSE100", "NIKKEI"] # indici da considerare
    prezzi = ["Open", "High", "Low", "Close", "Volume", "Close_prev"] # prezzi da considerare
    addons = [
        "gap_ret", "intra_ret", "range_pct", "tr", "atr7", "rv7", "rs_vol7", "beta14", "corr14", "boll_z20", "rsi14", "mae7", "mfe7", "half_life", "skew7", "kurt7"
    ] # add-ons da considerare
    for idx in indici: # per ogni indice, stampa prezzi e add-ons se presenti, a video
        print(f"--- {idx} ---")
        for p in prezzi:
            val = articolo.get(f"{idx}_{p}", None)
            print(f"  {p}: {val}")
        for a in addons:
            val = articolo.get(f"{idx}_{a}", None)
            print(f"  {a}: {val}")
    print()

    # il fetcher si occupa di recuperare notizie da feed RSS e stamparle a schermo, con funzioni di supporto per la visualizzazione dei prezzi associati alle notizie.