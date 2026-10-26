# IMF Validator - Validazione analisi pattern con metriche IMF
# Modulo di verifica incrociata con benchmark del Fondo Monetario Internazionale

import os
import requests
from deepseek_manager import call_deepseek

# Chiave API DeepSeek (stessa di deepseek_manager)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # chiave rimossa dai sorgenti: va revocata

# METRICHE DI RIFERIMENTO IMF
METRICHE_IMF = """
METRICHE DI RIFERIMENTO – SHOCK GEOPOLITICI (Fonte: IMF Research)
- Calo medio mensile dei prezzi azionari globali in corrispondenza di eventi geopolitici rilevanti: circa 1%
- Calo medio mensile dei mercati azionari nei paesi emergenti in fasi di tensione geopolitica: fino a circa 2,5%
- Calo tipico degli asset finanziari in presenza di crisi geopolitiche eccezionali (guerre, rotture diplomatiche, terrorismo su larga scala): nell'ordine di 1–3% su base mensile, con punte anche superiori nei contesti più fragili
- Aumento medio dei premi di rischio sovrano dopo eventi geopolitici significativi: circa 30 punti base nelle economie avanzate e 45 punti base nei mercati emergenti
- Effetti di durata: incremento dell'incertezza macrofinanziaria e della volatilità di mercato per diversi mesi dopo lo shock iniziale

METRICHE DI RIFERIMENTO – SHOCK FINANZIARI (Fonte: IMF Financial Stability Reports)
- Possibili correzioni dei mercati azionari in caso di shock finanziari gravi (crisi di fiducia, stress di liquidità, eventi sistemici): cali cumulati che possono facilmente superare il 10–20% in un orizzonte di breve periodo
- Aumento marcato degli spread di credito e dei premi per il rischio su debito sovrano e corporate
- Peggioramento delle condizioni di finanziamento e riduzione dell'offerta di credito a famiglie e imprese
- Maggiore volatilità dei flussi di capitale internazionali, con episodi di "flight to safety" verso asset sicuri

SOGLIE DI CLASSIFICAZIONE (basate su dati giornalieri/settimanali):
- GIORNALIERO: calo >1.5-2% = movimento anomalo
- SETTIMANALE (7 giorni): calo >3-5% = shock significativo  
- MENSILE: applicare metriche IMF standard

MAPPING CON ADD-ONS DEL SISTEMA:
- atr7/rv7 elevati (>1.5x media) → volatilità post-shock
- zscore7 < -2 → potenziale shock in corso
- drawdown > 5% → correzione significativa
- momentum7 fortemente negativo → trend ribassista consolidato
- intra_ret < -1.5% → sessione di panico
"""

GRIGLIA_CLASSIFICAZIONE = """
GRIGLIA DI CLASSIFICAZIONE EVENTI:
1. SHOCK GEOPOLITICO MODERATO:
   - Calo indici globali ~1%
   - Volatilità aumentata ma contenuta
   - Durata effetti: giorni/settimane

2. SHOCK GEOPOLITICO RILEVANTE:
   - Calo indici 1-3%
   - Aumento premi di rischio 30-45bp
   - Volatilità elevata persistente
   - Durata effetti: settimane/mesi

3. SHOCK FINANZIARIO GRAVE/SISTEMICO:
   - Correzioni cumulative >10-20%
   - Forte ampliamento spread
   - Flight to safety evidente
   - Crisi di liquidità
   - Durata effetti: mesi/anni
"""


def estrai_metriche_da_addons(addons):
    """
    Estrae metriche rilevanti dagli add-ons per la validazione IMF.
    """
    metriche_estratte = {}
    
    for indice in ["SP500", "NASDAQ", "DAX", "FTSE100", "NIKKEI"]:
        prefix = f"{indice}_"
        
        # Estrai valori rilevanti
        intra_ret = addons.get(f"{prefix}intra_ret", 0) or 0
        gap_ret = addons.get(f"{prefix}gap_ret", 0) or 0
        drawdown = addons.get(f"{prefix}drawdown", 0) or 0
        zscore7 = addons.get(f"{prefix}zscore7", 0) or 0
        atr7 = addons.get(f"{prefix}atr7", 0) or 0
        rv7 = addons.get(f"{prefix}rv7", 0) or 0
        momentum7 = addons.get(f"{prefix}momentum7", 0) or 0
        volatility7 = addons.get(f"{prefix}volatility7", 0) or 0
        
        metriche_estratte[indice] = {
            "variazione_giornaliera": round(intra_ret * 100, 2) if intra_ret else 0,
            "gap_apertura": round(gap_ret * 100, 2) if gap_ret else 0,
            "drawdown_pct": round(drawdown * 100, 2) if drawdown else 0,
            "zscore7": round(zscore7, 2) if zscore7 else 0,
            "volatilita_7g": round(volatility7 * 100, 2) if volatility7 else 0,
            "momentum7": round(momentum7, 2) if momentum7 else 0,
            "atr7": round(atr7, 2) if atr7 else 0
        }
    
    return metriche_estratte


def classifica_shock(metriche_estratte):
    """
    Classifica il tipo di shock basandosi sulle metriche estratte.
    """
    # Calcola medie globali
    cali_giornalieri = [abs(m["variazione_giornaliera"]) for m in metriche_estratte.values() if m["variazione_giornaliera"] < 0]
    drawdowns = [abs(m["drawdown_pct"]) for m in metriche_estratte.values()]
    zscores = [m["zscore7"] for m in metriche_estratte.values()]
    
    calo_medio = sum(cali_giornalieri) / len(cali_giornalieri) if cali_giornalieri else 0
    drawdown_max = max(drawdowns) if drawdowns else 0
    zscore_min = min(zscores) if zscores else 0
    
    # Classificazione
    if drawdown_max > 10 or calo_medio > 3:
        return "SHOCK_FINANZIARIO_GRAVE", {
            "calo_medio": calo_medio,
            "drawdown_max": drawdown_max,
            "zscore_min": zscore_min
        }
    elif drawdown_max > 3 or calo_medio > 1.5 or zscore_min < -2:
        return "SHOCK_GEOPOLITICO_RILEVANTE", {
            "calo_medio": calo_medio,
            "drawdown_max": drawdown_max,
            "zscore_min": zscore_min
        }
    elif calo_medio > 0.5 or zscore_min < -1:
        return "SHOCK_GEOPOLITICO_MODERATO", {
            "calo_medio": calo_medio,
            "drawdown_max": drawdown_max,
            "zscore_min": zscore_min
        }
    else:
        return "NESSUNO_SHOCK_RILEVATO", {
            "calo_medio": calo_medio,
            "drawdown_max": drawdown_max,
            "zscore_min": zscore_min
        }


def valida_analisi_con_imf(report_nesso, addons, titolo, data):
    """
    Valida un'analisi pattern confrontandola con le metriche IMF.
    Usa DeepSeek per generare un'analisi incrociata approfondita.
    """
    # Estrai metriche dagli add-ons
    metriche_estratte = estrai_metriche_da_addons(addons)
    
    # Classifica preliminare
    tipo_shock, stats = classifica_shock(metriche_estratte)
    
    # Prepara il prompt per DeepSeek
    prompt = f"""
Sei un analista del Fondo Monetario Internazionale (IMF) specializzato in shock geopolitici e finanziari.

COMPITO: Svolgi controlli incrociati tra l'analisi pattern fornita e le METRICHE DI RIFERIMENTO IMF per classificare e interpretare l'evento.

{METRICHE_IMF}

{GRIGLIA_CLASSIFICAZIONE}

---

ANALISI PATTERN DA VALIDARE:
Titolo: {titolo}
Data: {data}
Report: {report_nesso}

METRICHE ESTRATTE DAI DATI DI MERCATO:
{metriche_estratte}

CLASSIFICAZIONE PRELIMINARE AUTOMATICA: {tipo_shock}
- Calo medio giornaliero: {stats['calo_medio']:.2f}%
- Drawdown massimo: {stats['drawdown_max']:.2f}%
- Z-score minimo (7g): {stats['zscore_min']:.2f}

---

ISTRUZIONI:
1. Confronta i movimenti osservati con le METRICHE DI RIFERIMENTO IMF
2. Verifica se la classificazione automatica è corretta
3. Identifica le caratteristiche tipiche dello shock (se presente)
4. Descrivi le conseguenze tipiche secondo gli studi IMF
5. Fornisci una previsione sulla durata e intensità degli effetti

FORMATO RISPOSTA (segui esattamente questo schema):

TIPO DI SHOCK: [shock geopolitico moderato / shock geopolitico rilevante / shock finanziario grave / nessuno shock rilevato]

CONFRONTO CON METRICHE IMF:
- [confronto specifico con i benchmark]

CARATTERISTICHE TIPICHE RILEVATE:
- [elenco caratteristiche]

CONSEGUENZE ATTESE (secondo studi IMF):
- [conseguenze specifiche con dati numerici]

DURATA STIMATA EFFETTI: [giorni/settimane/mesi]

LIVELLO DI ALLERTA: [BASSO/MEDIO/ALTO/CRITICO]
"""

    # Chiama DeepSeek per l'analisi
    analisi_imf = call_deepseek(prompt, max_tokens=800, temperature=0.2)
    
    return {
        "titolo": titolo,
        "data": data,
        "tipo_shock": tipo_shock,
        "stats": stats,
        "metriche_estratte": metriche_estratte,
        "analisi_imf": analisi_imf
    }


def valida_tutti_i_risultati(risultati_lia):
    """
    Valida tutti i risultati dell'analisi LiA con le metriche IMF.
    Stampa un report finale strutturato.
    """
    print("\n" + "=" * 80)
    print("VALIDAZIONE IMF - Controllo Incrociato con Metriche Fondo Monetario Internazionale")
    print("=" * 80)
    
    validazioni = []
    
    for i, risultato in enumerate(risultati_lia, 1):
        titolo = risultato.get("titolo", "")
        data = risultato.get("data", "")
        report_nesso = risultato.get("report_nesso", "")
        
        # Recupera addons dal database se non presenti
        addons = risultato.get("addons", {})
        if not addons:
            # Prova a recuperare dal database
            try:
                import pandas as pd
                from db_manager import crea_database_se_necessario
                xlsx_path = crea_database_se_necessario()
                df = pd.read_excel(xlsx_path)
                mask = (df["Titolo"] == titolo) & (df["Data"] == data)
                if mask.any():
                    row = df[mask].iloc[0]
                    addons = {k: v for k, v in row.items() if any(x in k for x in 
                        ["gap_ret", "intra_ret", "drawdown", "zscore", "atr", "rv", "momentum", "volatility"])}
            except Exception:
                addons = {}
        
        if not report_nesso:
            continue
        
        print(f"\n{'─' * 80}")
        print(f"   Caso {i}) {titolo[:60]}{'...' if len(titolo) > 60 else ''}")
        print(f"   Data: {data}")
        print(f"{'─' * 80}")
        
        # Esegui validazione
        validazione = valida_analisi_con_imf(report_nesso, addons, titolo, data)
        validazioni.append(validazione)
        
        # Stampa risultato formattato
        print(f"\n   Analisi tra fonti IMF e pattern completata.")
        print(f"\n   Stando alle fonti IMF, il caso {i}) presenta tratti tipici di:")
        
        tipo = validazione["tipo_shock"].replace("_", " ").lower()
        if "nessuno" in tipo:
            print(f"     Nessuno shock rilevato - Condizioni di mercato normali")
        else:
            print(f"     Uno {tipo}")
        
        print(f"\n    Statistiche chiave:")
        print(f"      • Calo medio giornaliero: {validazione['stats']['calo_medio']:.2f}%")
        print(f"      • Drawdown massimo: {validazione['stats']['drawdown_max']:.2f}%")
        print(f"      • Z-score minimo (7g): {validazione['stats']['zscore_min']:.2f}")
        
        print(f"\n    Analisi dettagliata IMF:")
        # Formatta l'analisi con indentazione
        for line in validazione["analisi_imf"].split("\n"):
            if line.strip():
                print(f"      {line}")
        
        print()
    
    # Riepilogo finale
    print("\n" + "=" * 80)
    print("   RIEPILOGO VALIDAZIONE IMF")
    print("=" * 80)
    
    conteggio = {}
    for v in validazioni:
        tipo = v["tipo_shock"]
        conteggio[tipo] = conteggio.get(tipo, 0) + 1
    
    for tipo, count in conteggio.items():
        tipo_display = tipo.replace("_", " ").title()
        print(f"   • {tipo_display}: {count} casi")
    
    print(f"\n   Totale analisi validate: {len(validazioni)}")
    print("=" * 80 + "\n")
    
    return validazioni


def run_imf_validation(report_nesso_list):
    """
    Entry point principale per la validazione IMF.
    Prende la lista di report_nesso dall'analisi LiA e li valida.
    """
    # Converti in formato compatibile se necessario
    risultati = []
    for item in report_nesso_list:
        if isinstance(item, dict):
            risultati.append(item)
        else:
            risultati.append({"report_nesso": str(item)})
    
    return valida_tutti_i_risultati(risultati)


# Test del modulo
if __name__ == "__main__":
    print(" Test IMF Validator...")
    
    # Test con dati di esempio
    test_risultati = [{
        "titolo": "Crisi del debito sovrano europeo - Grecia annuncia default tecnico",
        "data": "2015-06-30",
        "report_nesso": "La Grecia ha annunciato il mancato pagamento al FMI, causando un crollo dei mercati europei. Il DAX ha perso il 3.5% intraday con volatilità elevata.",
        "addons": {
            "SP500_intra_ret": -0.02,
            "SP500_drawdown": -0.05,
            "SP500_zscore7": -1.8,
            "DAX_intra_ret": -0.035,
            "DAX_drawdown": -0.08,
            "DAX_zscore7": -2.5,
            "FTSE100_intra_ret": -0.025,
            "FTSE100_drawdown": -0.06,
            "FTSE100_zscore7": -2.0
        }
    }]
    
    valida_tutti_i_risultati(test_risultati)
