# Linked Intelligent Analyst (LiA) - LEGACY
# ⚠️ DEPRECATO: Questo modulo usa TF-IDF + OpenAI GPT-3.5
# Usa invece deepseek_manager.py con run_lia_deepseek() per analisi pattern (più accurato)

import os
import pandas as pd # importa la libreria pandas
import openai # importa la libreiria OpenAI
from dotenv import load_dotenv
from db_manager import crea_database_se_necessario # importa la funzione crea_database_se_necessario dal modulo db_manager per poter operare sul database
from sklearn.feature_extraction.text import TfidfVectorizer # importa TfidfVectorizer da sklearn per la vettorizzazione del testo
from sklearn.metrics.pairwise import cosine_similarity # importa cosine_similarity da sklearn per il calcolo della similarità del coseno

# Carica chiave API da variabile ambiente (mai hardcodare!)
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')


def run_lia(report_nesso_list, soglia_similarita=0.0): # recupera tutti i report_nesso e li confronta con quelli che hanno una bassissima soglia di similarità
    # prompt per l'analisi AI, da arricchire per migliorare i risultati
    """
    Per ogni nuovo report_nesso in report_nesso_list, confronta con tutto il database e stampa la sentenza AI. 
    report_nesso_list: lista di dict con almeno Titolo, Data, report_nesso
    """
    xlsx_path = crea_database_se_necessario() # crea il database se non esiste e ne recupera il percorso
    df_db = pd.read_excel(xlsx_path) # legge il file excel e lo carica in un dataframe pandas
    df_db = df_db.dropna(subset=["report_nesso"]) # rimuove le righe senza report_nesso
    if df_db.empty: # if, se il dataframe è vuoto, stampa un messaggio di avviso e termina la funzione
        print("⚠️ Nessun report_nesso disponibile nel database.")
        return
    db_reports = df_db["report_nesso"].astype(str).tolist() # converte la colonna report_nesso in una lista di stringhe per favorire l'elaborazione
    vectorizer = TfidfVectorizer() # inizializza il vettorizzatore TF-IDF
    tfidf_db = vectorizer.fit_transform(db_reports) # trasforma i report_nesso del database in una matrice TF-IDF
    for articolo in report_nesso_list: # per ogni articolo nella lista report_nesso_list
        titolo = articolo.get("Titolo", "") # recupera il titolo dell'articolo
        data = articolo.get("Data", "") # recupera la data dell'articolo
        report_nesso = articolo.get("report_nesso", "") # recupera il report_nesso dell'articolo
         # se il report_nesso è vuoto, salta all'articolo successivo
        if not report_nesso:
            continue
        tfidf_new = vectorizer.transform([report_nesso]) # trasforma il nuovo report_nesso in una matrice TF-IDF
         # calcola la similarità del coseno tra il nuovo report_nesso e tutti quelli del database
        cosine_sim = cosine_similarity(tfidf_new, tfidf_db).flatten() # calcola la similarità del coseno tra il nuovo report_nesso e tutti quelli del database
         # trova gli indici dei report_nesso con similarità sopra la soglia, FUNZIONE PARZIALMENTE INUTILE, OCCORRE RIVEDERLA PERCHÉ CON SOGLIA 0.0 RESTITUISCE TUTTI I RISULTATI, ma con valore superiore non restituisce nulla
        simili_idx = [i for i, sim in enumerate(cosine_sim) if sim >= soglia_similarita] 
        if simili_idx: # se ci sono report_nesso simili
            # prepara il contesto con esempi storici tramite esempi=[]
            esempi = []
            for i in simili_idx: # per ogni indice simile dove i è l'indice del report_nesso simile
                 # recupera il report_nesso, SP500_Close e SP500_Close_prev dal dataframe
                row_db = df_db.iloc[i] # recupera la riga corrispondente all'indice i
                report = row_db["report_nesso"] # recupera il report_nesso
                close = row_db.get("SP500_Close")   # recupera il valore di chiusura S&P500
                prev = row_db.get("SP500_Close_prev") # recupera il valore di chiusura precedente S&P500
                 # determina se c'è stato un aumento o una diminuzione del mercato
                if pd.notna(close) and pd.notna(prev): # se entrambi i valori non sono NaN
                     # determina se c'è stato un aumento o una diminuzione del mercato
                    movimento = "aumento" if close > prev else "diminuzione"
                    esempi.append(f"- {report} → {movimento}")
                else: # se uno dei valori è NaN, aggiunge solo il report_nesso senza movimento
                    esempi.append(f"- {report}") 
            contesto = "\n".join(esempi) # unisce gli esempi in una singola stringa separata da nuove righe
             # prepara il prompt per l'analisi AI
            prompt = f"""
Agisci come un analista finanziario che confronta eventi recenti con la storia.
Ho un nuovo report_nesso:

'{report_nesso}'

Ti fornisco alcuni esempi storici con il loro impatto sui mercati (S&P500 Close vs Close_prev):

{contesto}

OBIETTIVI:
1. Trova le analogie semantiche tra il nuovo report e gli esempi passati.
2. Conta quanti casi storici simili hanno portato ad aumenti, e quanti a diminuzione.
3. Fornisci una sintesi breve e numerica alla quale aggiungi in fondo il calcolo percentuale riguardo alle diminuzioni o agli aumenti di prezzo, ad esempio:
   "5 casi simili su 7 hanno portato a aumento, 2 a diminuzione, 71,4% volte, casi simili hanno prodotto aumenti. 28.6% volte sono stati riscontrati ribassi".
4. Concludi con una frase interpretativa (max 1 riga) tipo:
   "In contesti di inflazione + taglio tassi storicamente i mercati hanno reagito positivamente".
"""
            try: # chiama l'API OpenAI per ottenere la sintesi dei dati precedentemente recuperati
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", # utilizza il modello gpt-3.5-turbo per fornire risposte, con maggiori fondi è possibile salire a modelli più recenti e performanti
                    messages=[{"role": "user", "content": prompt}], 
                    max_tokens=400, # limita la risposta a 400 token
                    temperature=0.2 # imposta la temperatura a 0.2 per risposte più coerenti e meno casuali
                )
                sintesi = response.choices[0].message.content.strip() # estrae il contenuto della risposta, fornendo una sintesi dell'analisi
            except Exception as e: # in caso di errore durante la chiamata all'API, cattura l'eccezione e stampa un messaggio di errore per evitare di avere errori e blocchi a schermo
                sintesi = f"Errore AI: {e}"
            print(f"\n📌 Report: {titolo} ({data})") # stampa il titolo e la data del report in caso di NON errore
            print(sintesi) # stampa la sintesi ottenuta dall'analisi AI in caso di NON errore

            # l'obiettivo di questo script è di fornire un'analisi IA basata su esempi storici,
            # aiutando l'utente a comprendere meglio il possibile impatto di eventi attuali.
            # l'obiettivo è quello di ottenere un confronto tra parole e numeri, per quanto possibile, visti i limiti di comunicazione tra le varie tipologia di IA (in questo caso, linguistica generativa e di calcolo)