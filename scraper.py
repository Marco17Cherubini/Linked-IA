import requests # per fare richieste HTTP
from bs4 import BeautifulSoup # per fare scraping HTML
import re # per operazioni con espressioni regolari

# Lista base di stopword/congiunzioni da rimuovere per favorire l'analisi del testo tramite embedding
STOPWORDS = {
    "e", "o", "ma", "per", "con", "di", "a", "da", "in", "su", "il", "la", "lo", "gli", "le", "un", "una", "che", "al", "ai", "del", "della", "dello", "dei", "delle", "ed", "ad"
}

def pulisci_testo(testo): 
    # Minuscolo
    testo = testo.lower()
    # Rimuovi caratteri non alfabetici (eccetto spazi)
    testo = re.sub(r'[^a-zàèéìòù\s]', '', testo)
    # Rimuovi spazi multipli
    testo = re.sub(r'\s+', ' ', testo)
    # Rimuovi stopword/congiunzioni
    parole = [p for p in testo.split() if p not in STOPWORDS]
    return ' '.join(parole).strip()

def scrape_articles(df): # prende un dataframe con almeno Fonte, Titolo, Corpo, Link, Data e restituisce una lista di dettagli con testo pulito, rimuovendo tutto quello scritto qui di sopra per favorire analisi semantica e testuale dell'IA
    dettagli = [] 
    for _, row in df.iterrows(): # per ogni riga del dataframe, recupera il testo pulito
        titolo, corpo = "", ""
        if row.get("Fonte", "") == "OpenAI":
            titolo = pulisci_testo(row.get("Titolo", "")) # pulisce il titolo
            corpo = pulisci_testo(row.get("Corpo", "")) # pulisce il corpo
        elif "Link" in row and row["Link"]: # se c'è un link, prova a fare scraping
            titolo, corpo = scrape_article(row.get("Fonte", ""), row["Link"], row.get("Data", ""))
            titolo = pulisci_testo(titolo)
            corpo = pulisci_testo(corpo)
        else: # altrimenti usa quello che c'è nel dataframe
            titolo = pulisci_testo(row.get("Titolo", ""))
            corpo = pulisci_testo(row.get("Corpo", ""))
        dettagli.append({ #
            "Fonte": row.get("Fonte", ""),
            "Titolo": titolo,
            "Corpo": corpo,
            "Link": row.get("Link", ""),
            "Data": row.get("Data", "")
        })
    return dettagli # restituisce la lista di dettagli con testo pulito alla fine di questa parte di script

def scrape_article(source, url, date_filter=None): # funzione di scraping per fonti specifiche, attualmente Investing, CNBC e Reuters
    try: 
        headers = {"User-Agent": "Mozilla/5.0"}
        page = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(page.content, 'html.parser')
        titolo, corpo = "", ""
        if source == "Investing": # parte di script specifica per Investing.com
            titolo_tag = soup.find("h1", id="articleTitle")
            corpo_tag = soup.find("div", class_="article_WYSIWYG__O0uhw article_articlePage")
            titolo = titolo_tag.text.strip() if titolo_tag else ""
            corpo = corpo_tag.get_text(separator="\n", strip=True) if corpo_tag else ""
        elif source == "CNBC": # parte di script specifica per CNBC
            titolo_tag = soup.find("h1", class_="ArticleHeader-headline")
            corpo_tag = soup.find("div", class_="group")
            titolo = titolo_tag.text.strip() if titolo_tag else ""
            corpo = corpo_tag.get_text(separator="\n", strip=True) if corpo_tag else ""
        elif source == "Reuters": # parte di script specifica per Reuters
            titolo_tag = soup.find("h1", {"data-testid": "Heading"})
            corpo_tag = soup.find("div", class_="article-body__content__17Yit")
            titolo = titolo_tag.text.strip() if titolo_tag else ""
            corpo = corpo_tag.get_text(separator="\n", strip=True) if corpo_tag else ""
        return titolo, corpo # restituisce titolo e corpo dai vari siti, recuperandoli tra il linguaggio HTML
    except Exception as e: # in caso di errore, stampa l'errore e restituisce stringhe vuote
        print(f"[!] Errore scraping {source} - {url}: {e}")
        return "", ""
    
    # Lo script di scraping è progettato per estrarre e pulire il testo da articoli di notizie finanziarie direttamente dal HTML, rimuovendo elementi non testuali o d'intralcio per facilitare l'analisi successiva tramite modelli di intelligenza artificiale.