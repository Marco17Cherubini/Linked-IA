import requests # importa la libreria requests per chiamate HTTP all'API di Perplexity
import os # per gestire variabili d'ambiente
from datetime import datetime, timedelta # importa le classi datetime e timedelta per la gestione delle date
from dotenv import load_dotenv # per caricare variabili d'ambiente dal file .env

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Configurazione API Perplexity
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_BASE_URL = "https://api.perplexity.ai/chat/completions"

def selezione_intelligente(date_str): # definisce la funzione che sostituisce collegamenti con database a pagamento come Factiva. Cerca eventi storici rilevanti per la data specificata in maniera tale da poter eseguire un'analisi geopolitica-finanziaria a prescindere dalla presenza di database
    """
    Cerca eventi per la data richiesta.
    Restituisce: lista di articoli [{"data": data, "titolo": titolo, "corpo": corpo}]
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d") # Converte la stringa in oggetto datetime
    articoli = [] # Lista per memorizzare gli articoli trovati
    
    # Prima cerca esattamente per la data richiesta
    articolo = chiedi_articolo_perplexity(date_str)
    if articolo and articolo["titolo"].lower() != "nessun evento" and articolo.get("fonti"):
        articolo["data"] = date_str
        articoli.append(articolo)
    
    # Se non trova nulla, cerca nei giorni vicini
    if not articoli:
        for delta in [-1, 1, -2, 2]:
            nuova_data = (date_obj + timedelta(days=delta)).strftime("%Y-%m-%d")
            articolo = chiedi_articolo_perplexity(nuova_data) 
            if articolo and articolo["titolo"].lower() != "nessun evento" and articolo.get("fonti"):
                articolo["data"] = nuova_data
                articoli.append(articolo)
                break  # Trova almeno un articolo
    
    return articoli

def chiedi_articolo_perplexity(date_str): # funzione che interroga il modello Perplexity per ottenere un articolo rilevante per la data specificata con ricerca online
    prompt = (
    f"Ricerca online il giorno {date_str} e trova SEMPRE almeno un evento significativo. "
    f"Cerca tra: eventi geopolitici (guerre, elezioni, tensioni), economici (decisioni banche centrali, dati macro, mercati), "
    f"aziendali (fusioni, acquisizioni, risultati trimestrali importanti), tecnologici (innovazioni, regolamentazioni), "
    f"sociali (proteste, cambiamenti legislativi), naturali (disastri, clima) o culturali rilevanti per i mercati. "
    f"\nSe non trovi eventi MAGGIORI, cerca eventi MINORI ma comunque documentati. "
    f"Esempi di eventi minori: riunioni BCE/Fed, pubblicazione dati inflazione/PIL, "
    f"decisioni aziendali rilevanti, annunci politici, cambiamenti normativi. "
    f"\nSolo se DAVVERO non trovi nulla di documentato per il {date_str}, rispondi 'TITOLO: Nessun evento'. "
    f"Ma prova sempre a trovare almeno qualcosa di rilevante per l'analisi finanziaria. "
    f"\nIMPORTANTE: NON usare riferimenti numerici come [1], [2], [3] nel testo. Scrivi in modo discorsivo e pulito. "
    f"\nFormato richiesto:\n"
    f"TITOLO: [evento specifico con data]\n"
    f"CORPO: [descrizione con contesto economico-finanziario, SENZA citazioni numerate]\n"
    f"FONTI: [2-3 URL completi separati da punto e virgola]\n"
)

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar-pro",  # Modello Sonar Pro con ricerca online
        "messages": [
            {
                "role": "system", 
                "content": "Sei un analista geopolitico-finanziario esperto. Rispondi solo con informazioni verificate da fonti online autorevoli. NON usare MAI riferimenti numerici come [1], [2], [3] nel testo - scrivi in modo discorsivo e pulito."
            },
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.2,
        "top_p": 0.9,
        "return_citations": True
    }

    try: # Interroga l'API di Perplexity per trovare notizie verificate online
        response = requests.post(PERPLEXITY_BASE_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        testo = data['choices'][0]['message']['content'].strip()
        
        # Parsing del formato richiesto
        titolo, corpo, fonti = "", "", []
        for line in testo.split('\n'):
            line = line.strip()
            if line.upper().startswith("TITOLO:"):
                titolo = line.split(":", 1)[1].strip()
            elif line.upper().startswith("CORPO:"):
                corpo = line.split(":", 1)[1].strip()
            elif line.upper().startswith("FONTI:"):
                fonti_str = line.split(":", 1)[1].strip()
                fonti = [f.strip() for f in fonti_str.split(';') if f.strip()]
            elif corpo != "" and not line.upper().startswith("FONTI:") and line:
                corpo += " " + line
        
        # Se Perplexity include citazioni, estrai anche quelle come fonti aggiuntive
        if 'citations' in data and data['citations']:
            citations = [cite for cite in data['citations'] if cite]
            if citations and not fonti:
                fonti = citations[:3]  # Prendi le prime 3 citazioni
        
        return {"titolo": titolo, "corpo": corpo, "fonti": fonti}
        
    except requests.exceptions.RequestException as e:
        print(f"Errore connessione Perplexity API: {e}")
        return {"titolo": "Nessun evento", "corpo": ""}
    except Exception as e: # Gestione degli errori in caso di problemi
        print(f"Errore Perplexity: {e}")
        return {"titolo": "Nessun evento", "corpo": ""}
