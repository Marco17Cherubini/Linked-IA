# DeepSeek Manager - Analisi pattern notizie/mercato con DeepSeek AI
# Sostituisce GPT-3.5/4 per l'analisi semantica e pattern matching

import os
import requests
import pandas as pd
from db_manager import crea_database_se_necessario

# Chiave API DeepSeek
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # chiave rimossa dai sorgenti: va revocata
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"


def call_deepseek(prompt, max_tokens=1000, temperature=0.3):
    """
    Chiama l'API DeepSeek per ottenere una risposta al prompt fornito.
    DeepSeek utilizza un formato compatibile con OpenAI.
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",  # modello principale DeepSeek
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(DEEPSEEK_BASE_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        return f"Errore DeepSeek API: {e}"
    except (KeyError, IndexError) as e:
        return f"Errore parsing risposta DeepSeek: {e}"


def analizza_articolo_deepseek(titolo, corpo, fonti, data, prezzi, addons):
    """
    Analizza un singolo articolo usando DeepSeek per comprendere il contenuto
    e generare un report_nesso che collega notizia e mercato.
    """
    contesto = f"""
Fonti: {fonti}
Data: {data}
Titolo: {titolo}
Corpo: {corpo}
Prezzi OHLCV: {prezzi}
Add-ons: {addons}
"""
    
    prompt = f"""
Analizza la seguente notizia e confrontala con i dati di mercato forniti.

OBIETTIVI:
1. Ricostruisci e comprendi il contenuto dell'articolo dalle parole chiave fornite (titolo e corpo già puliti da stopword).
2. Identifica gli eventi rilevanti: crisi, guerre, attentati, decisioni politiche, dati macroeconomici, annunci aziendali.
3. Valuta se l'evento è tipicamente associato a impatti sui mercati finanziari basandoti sulla tua conoscenza.
4. Analizza i prezzi OHLCV e gli indicatori add-on. Se un valore è mancante, deduci il significato dal nome.
5. Collega semanticamente la notizia ai movimenti nei dati. Esplicita associazioni con cali, volatilità, inversioni, gap.
6. Non inventare dati. Se non trovi prove nei dati, indica che non ci sono segnali evidenti.
7. Rispondi in massimo **3 righe**, sintetico, preciso, con riferimenti ai dati quando possibile.

SIGNIFICATO ADD-ONS:
- gap_ret = differenza apertura/chiusura precedente (gap di mercato)
- intra_ret = variazione intra-day
- range_pct = range percentuale giornaliero
- tr = true range, escursione giornaliera
- atr7 = average true range 7 giorni (volatilità media)
- rv7 = realized volatility 7 giorni
- rs_vol7 = volatilità Rogers-Satchell
- rolling_min7/max7 = minimo/massimo rolling 7 giorni
- zscore7 = distanza dalla media 7 giorni in deviazioni standard
- percentile7 = posizione percentile nel range 7 giorni
- drawdown = calo massimo dal picco
- momentum7 = differenza prezzo attuale vs 7 giorni dopo (forward-looking)
- volatility7 = volatilità annualizzata 7 giorni

{contesto}
"""
    return call_deepseek(prompt, max_tokens=500, temperature=0.3)


def run_analysis_deepseek(articoli_completi):
    """
    Analizza una lista di articoli con DeepSeek.
    Sostituisce run_analysis_incrementale di analizer2.py.
    Restituisce lista di dict con Titolo, Data, report_nesso.
    """
    report_nesso_list = []
    
    for i, articolo in enumerate(articoli_completi, 1):
        titolo = str(articolo.get("Titolo", ""))
        corpo = str(articolo.get("Corpo", ""))
        fonti = str(articolo.get("Fonti", ""))
        data = str(articolo.get("Data", ""))
        prezzi = articolo.get("prezzi", {})
        addons = articolo.get("addons", {})
        
        print(f"\n [{i}/{len(articoli_completi)}] Analisi DeepSeek: {titolo[:50]}...")
        
        report_nesso = analizza_articolo_deepseek(titolo, corpo, fonti, data, prezzi, addons)
        
        print(f"TITOLO: {titolo}")
        print(f"DATA: {data}")
        print(f"PREZZI: {prezzi}")
        print(f"ADD-ONS: {addons}")
        print(f"REPORT NESSO:\n{report_nesso}")
        print("-" * 60)
        
        report_nesso_list.append({
            "Titolo": titolo,
            "Data": data,
            "report_nesso": report_nesso
        })
    
    return report_nesso_list


def trova_pattern_storici(report_nesso_nuovo, soglia_keywords=3):
    """
    Trova pattern storici nel database che hanno parole chiave comuni con il nuovo report.
    Restituisce una lista di tuple (report_storico, movimento, score_similarita).
    """
    xlsx_path = crea_database_se_necessario()
    df_db = pd.read_excel(xlsx_path)
    df_db = df_db.dropna(subset=["report_nesso"])
    
    if df_db.empty:
        return []
    
    # Estrai parole chiave dal nuovo report (parole > 4 caratteri)
    parole_nuovo = set(p.lower() for p in report_nesso_nuovo.split() if len(p) > 4)
    
    pattern_trovati = []
    for _, row in df_db.iterrows():
        report_storico = str(row["report_nesso"])
        parole_storico = set(p.lower() for p in report_storico.split() if len(p) > 4)
        
        # Conta parole in comune
        parole_comuni = parole_nuovo & parole_storico
        score = len(parole_comuni)
        
        if score >= soglia_keywords:
            close = row.get("SP500_Close")
            prev = row.get("SP500_Close_prev")
            
            if pd.notna(close) and pd.notna(prev):
                movimento = "UP" if close > prev else "DOWN"
            else:
                movimento = "UNKNOWN"
            
            pattern_trovati.append({
                "report": report_storico,
                "movimento": movimento,
                "score": score,
                "parole_comuni": list(parole_comuni),
                "data": row.get("Data", ""),
                "close": close,
                "close_prev": prev
            })
    
    # Ordina per score decrescente
    pattern_trovati.sort(key=lambda x: x["score"], reverse=True)
    return pattern_trovati


def analizza_pattern_mercato(report_nesso_nuovo, max_esempi=10):
    """
    Analizza pattern storici simili usando DeepSeek per predire il comportamento del mercato.
    Combina analisi semantica con dati storici del database.
    """
    pattern = trova_pattern_storici(report_nesso_nuovo, soglia_keywords=2)
    
    if not pattern:
        return {
            "predizione": "NEUTRO",
            "confidenza": 0.0,
            "up_count": 0,
            "down_count": 0,
            "analisi": "Nessun pattern storico simile trovato nel database."
        }
    
    # Limita agli esempi più rilevanti
    pattern = pattern[:max_esempi]
    
    # Conta UP e DOWN
    up_count = sum(1 for p in pattern if p["movimento"] == "UP")
    down_count = sum(1 for p in pattern if p["movimento"] == "DOWN")
    total = up_count + down_count
    
    if total == 0:
        return {
            "predizione": "NEUTRO",
            "confidenza": 0.0,
            "up_count": 0,
            "down_count": 0,
            "analisi": "Dati insufficienti per determinare pattern."
        }
    
    # Calcola percentuali
    up_pct = (up_count / total) * 100
    down_pct = (down_count / total) * 100
    
    # Prepara contesto per DeepSeek
    esempi_str = "\n".join([
        f"- Data: {p['data']}, Movimento: {p['movimento']}, "
        f"Parole comuni: {', '.join(p['parole_comuni'][:5])}"
        for p in pattern
    ])
    
    prompt = f"""
Sei un analista finanziario esperto. Analizza il seguente scenario:

NUOVO REPORT DA ANALIZZARE:
"{report_nesso_nuovo}"

PATTERN STORICI SIMILI TROVATI ({total} casi):
{esempi_str}

STATISTICHE:
- Casi con mercato UP: {up_count} ({up_pct:.1f}%)
- Casi con mercato DOWN: {down_count} ({down_pct:.1f}%)

COMPITI:
1. Identifica i temi comuni tra il nuovo report e i casi storici.
2. Spiega perché questi pattern sono rilevanti per prevedere il mercato.
3. Basandoti sui dati storici, indica la direzione più probabile (UP o DOWN).
4. Assegna un livello di confidenza (basso/medio/alto) basato sulla coerenza dei pattern.
5. Concludi con una frase interpretativa su come il mercato potrebbe reagire.

Rispondi in modo strutturato e conciso (max 5 righe).
"""
    
    analisi_deepseek = call_deepseek(prompt, max_tokens=600, temperature=0.2)
    
    # Determina predizione basata su statistiche
    if up_pct > 60:
        predizione = "UP"
        confidenza = up_pct / 100
    elif down_pct > 60:
        predizione = "DOWN"
        confidenza = down_pct / 100
    else:
        predizione = "NEUTRO"
        confidenza = max(up_pct, down_pct) / 100
    
    return {
        "predizione": predizione,
        "confidenza": confidenza,
        "up_count": up_count,
        "down_count": down_count,
        "up_pct": up_pct,
        "down_pct": down_pct,
        "pattern_count": total,
        "analisi": analisi_deepseek
    }


def run_lia_deepseek(report_nesso_list):
    """
    Esegue l'analisi LiA (Linked Intelligent Analyst) usando DeepSeek.
    Per ogni report_nesso, trova pattern simili e genera predizioni.
    Sostituisce run_lia di LiA.py.
    """
    print("\n" + "=" * 70)
    print(" Avvio analisi LiA (Pattern Matching)..."    )
    print("=" * 70)
    
    risultati = []
    
    for articolo in report_nesso_list:
        titolo = articolo.get("Titolo", "")
        data = articolo.get("Data", "")
        report_nesso = articolo.get("report_nesso", "")
        
        if not report_nesso:
            continue
        
        print(f"\n Analisi pattern per: {titolo[:50]}...")
        
        risultato = analizza_pattern_mercato(report_nesso)
        
        print(f"\n Report: {titolo} ({data})")
        print(f" Predizione: {risultato['predizione']} (confidenza: {risultato['confidenza']:.1%})")
        print(f" Statistiche storiche: {risultato['up_count']} UP, {risultato['down_count']} DOWN")
        print(f"\n Analisi:")
        print(risultato['analisi'])
        print("-" * 70)
        
        risultati.append({
            "titolo": titolo,
            "data": data,
            "report_nesso": report_nesso,
            **risultato
        })
    
    return risultati


# Funzione di test
if __name__ == "__main__":
    # Test della connessione DeepSeek
    print(" Test connessione API...")
    test_response = call_deepseek("Rispondi con 'OK' se funziona.", max_tokens=10)
    print(f"Risposta test: {test_response}")
    
    # Test analisi pattern con report di esempio
    print("\n Test analisi pattern...")
    report_test = "La Federal Reserve ha annunciato un aumento dei tassi di interesse, causando preoccupazione nei mercati azionari."
    risultato = analizza_pattern_mercato(report_test)
    print(f"Predizione: {risultato['predizione']}")
    print(f"Confidenza: {risultato['confidenza']:.1%}")
    print(f"Analisi: {risultato['analisi']}")
