# analizer2.py - LEGACY (GPT-3.5)
# ⚠️ DEPRECATO: Questo modulo usa OpenAI GPT-3.5
# Usa invece deepseek_manager.py con run_analysis_deepseek() per analisi pattern

import os
import openai # importa la libreria OpenAI per interagire con i modelli di linguaggio
import pandas as pd # consente il lavoro con DataFrame
from dotenv import load_dotenv

# Carica chiave API da .env (mai hardcodare!)
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

def run_analysis_incrementale(articoli_completi): # definisce la funzione che esegue l'analisi incrementale degli articoli trovati e si occupa di gettare le fondamenta per LiA e la sua funzionalità di analisi ultima
    """
    Analizza la lista articoli_completi, stampa a schermo e restituisce una lista di dict con Titolo, Data, report_nesso.
    """
    report_nesso_list = [] # Lista per memorizzare i report dei nessi
    for articolo in articoli_completi:
        titolo = str(articolo.get("Titolo", ""))
        corpo = str(articolo.get("Corpo", ""))
        fonti = str(articolo.get("Fonti", ""))
        data = str(articolo.get("Data", ""))
        prezzi = articolo.get("prezzi", {})
        addons = articolo.get("addons", {})

        contesto = f"""
Fonti: {fonti}
Data: {data}
Titolo: {titolo}
Corpo: {corpo}
Prezzi OHLCV: {prezzi}
Add-ons: {addons}
"""
        prompt = f""" 
Analizza la seguente notizia e confrontala con i dati forniti.

OBIETTIVI:
1. Comprendi il contenuto della notizia, individuando eventi rilevanti (es. crisi, guerre, attentati, decisioni politiche, eventi macroeconomici).
2. Valuta se l’evento è, per esperienza e conoscenza generale, tipicamente associato a un impatto sui mercati finanziari.
3. Analizza i prezzi e gli indicatori add-on forniti. Se un valore è vuoto o mancante, cerca di dedurre il suo significato basandoti sul nome dell’indicatore e sulla tua conoscenza delle metriche finanziarie.
4. Collega il contenuto semantico della notizia ai movimenti rilevati nei dati. Se i dati mostrano un calo, volatilità, inversioni, gap ecc., esplicita l’associazione.
5. Non inventare dati o effetti. Se non trovi prove nei dati, puoi dire che non ci sono segnali evidenti.
6. Rispondi in massimo **2 righe**, in modo sintetico, preciso e con riferimento ai dati quando possibile.

SIGNIFICATO DEGLI ADD-ONS:
- gap_ret = differenza tra l’apertura e la chiusura precedente (gap di mercato)
- intra_ret = variazione intra-day
- tr = true range, misura di escursione giornaliera
- atr7 = average true range a 7 giorni, stima della volatilità media recente
- rv7 = realized volatility a 7 giorni, altra metrica di rischio
- rs_vol7 = volatilità stimata con metodo Rogers–Satchell
- zscore7 = quanto il prezzo attuale è distante dalla media a 7 giorni
- drawdown = calo massimo dal picco
- momentum7 = differenza tra il prezzo attuale e quello di 7 giorni fa.
{contesto}
"""
        try: # Interroga il modello GPT-3.5-turbo per ottenere il report del nesso tramite il prompt sopra descritto, analizzando fino a 1000 token per fornire la risposta più consona
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            report_nesso = response.choices[0].message.content.strip() 
        except Exception as e:
            report_nesso = f"Errore AI: {e}"
        print(f"\nTITOLO: {titolo}\nDATA: {data}")
        print(f"PREZZI: {prezzi}")
        print(f"ADD-ONS: {addons}")
        print(f"REPORT NESSO (max 5 righe):\n{report_nesso}\n{'-'*60}")
        report_nesso_list.append({"Titolo": titolo, "Data": data, "report_nesso": report_nesso})
    return report_nesso_list

# Questa funzione è il cuore dell'analisi incrementale, in quanto consente di collegare la semantica (notizie) con il numerico (prezzi e add-ons), gettando le basi per l'analisi finale di LiA. Le sue risposte sintetiche e precise sono fondamentali per l'efficacia del ML.

