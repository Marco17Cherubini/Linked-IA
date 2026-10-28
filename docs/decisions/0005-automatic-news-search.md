# 0005 — Ricerca automatica delle notizie per data

**Stato**: accettata (28 ottobre 2026). **Sostituisce** la parte della decisione D2 di `docs/refactoring-plan.md` che rendeva manuale l'inserimento degli eventi.

> La ricerca automatica delle notizie per data è una capacità centrale di LiA. Non può essere sostituita dall'inserimento manuale senza un'esplicita richiesta dell'utente.

## Contesto

Il refactoring del 26 ottobre (commit `d0d6ad0`) ha rimosso `fetcher.py`, `scraper.py` e `archive_manager.py`. I problemi erano reali: feed RSS dismessi, selettori di scraping obsoleti, URL scritti liberamente da un modello (`sonar-pro`), errori trasformati in «Nessun evento», un fallback che chiedeva prezzi a un LLM. La soluzione però ha eliminato anche la funzione principale del prodotto: partire da una data e trovare gli eventi.

## Valutazione

| Criterio | Giudizio |
|---|---|
| Utilità | Alta: ripristina il percorso accesso → data → eventi → analisi senza compilare la notizia. |
| Affidabilità storica | Limitata e dichiarata. Le date di pubblicazione possono mancare o essere errate; gli esempi ufficiali dei filtri restituiscono risultati fuori intervallo. LiA ricontrolla ogni data sul server. La copertura delle fonti di decenni fa non è documentata dal provider. |
| Costo | Search API: 5 USD per 1.000 richieste (0,005 USD), fino a 5 query per richiesta. Una ricerca usa al massimo 2 richieste, più eventuali retry certamente non fatturati e un'estrazione facoltativa con DeepSeek. Tetto per ricerca: 0,05 USD (`LIA_NEWS_SEARCH_MAX_USD`). |
| Compatibilità | Riusa accesso, CSRF, budget, job esclusivi, analisi e regola prudente sugli eventi senza orario. |
| Limiti non eliminabili | Indice e ranking del provider; estratti brevi al posto degli articoli completi; nessuna ricerca è esaustiva. |

## Decisione

- **Recupero**: Perplexity Search API (`POST /search`), che restituisce risultati grezzi (titolo, URL, estratto, data di pubblicazione dichiarata). Non si usa Sonar in chat: genera testo libero, gli URL sarebbero scritti dal modello, e il prodotto risulta supportato solo fino al 27 settembre 2026.
- **Due tipi di richiesta**: *contemporanea* (pubblicate tra il primo giorno cercato e due giorni dopo l'ultimo) e *retrospettiva* (pubblicate dal giorno cercato in poi, con la data nella query). La modalità predefinita le usa entrambe; le schede indicano «Fonti dell'epoca» o «Solo fonti successive».
- **Controllo temporale lato server**: un risultato contemporaneo senza data o fuori finestra viene escluso; un risultato pubblicato prima dell'evento viene escluso; le esclusioni sono conteggiate e mostrate.
- **Schede deterministiche**: normalizzazione degli URL, deduplicazione, raggruppamento per somiglianza dei titoli, copie sindacate contate una volta, categoria ed etichette proposte da parole chiave, avvertenze esplicite. Funzionano senza alcun modello linguistico.
- **Estrazione facoltativa con DeepSeek**: il modello riceve gruppi numerati e può solo unirli, scrivere titolo e descrizione, proporre categoria, etichette e data nell'intervallo. URL, fonti e date di pubblicazione vengono sempre dai risultati del provider; l'output non conforme viene ignorato.
- **Analisi**: «Analizza questo evento» crea un evento privato (`origin = "search"`, `time_precision = "unknown"`) con fonti e date di pubblicazione, e avvia l'analisi esistente. La correzione manuale è facoltativa.
- **Errori**: provider non configurato, credenziali rifiutate, timeout, limite del provider, credito esaurito, budget e risposte illeggibili hanno codici e messaggi propri. Una ricerca riuscita senza risultati ha lo stato `empty`; con una sola richiesta fallita `partial`.
- **Costi**: ogni richiesta e ogni retry passa da `run_paid` (riserva atomica prima dell'invio, riconciliazione, esiti incerti trattenuti). Ricerche identiche entro 6 ore (date recenti) o 30 giorni (date storiche) riusano il risultato salvato; una ricerca identica in corso viene riusata. Un solo job esterno alla volta.
- **Dati conservati**: parametri, richieste inviate, URL, titolo, editore, date ed estratto (massimo 500 caratteri) per 90 giorni; le ricerche da cui è nato un evento analizzato restano finché resta l'evento. Mai il testo integrale degli articoli.

## Regole temporali e metodologiche

- Data dell'evento, data di pubblicazione, data di aggiornamento e momento del recupero restano distinti in tutte le strutture.
- Ricerca su un giorno: la data dell'evento è il giorno cercato. Su un intervallo: la prima pubblicazione dell'epoca nell'intervallo, segnalata come stima, oppure la data indicata nelle fonti (estrazione validata nell'intervallo).
- Nessun orario viene inventato: si applica la convenzione prudente della seduta base (ultima seduta chiusa prima del giorno dell'evento), che tiene conto di fusi, festività e chiusure perché usa le sedute effettivamente presenti nei dati di mercato.
- Gli eventi sono ordinati per numero di fonti indipendenti e per presenza di fonti dell'epoca, mai per i rendimenti successivi, che al momento della ricerca non vengono consultati.

## Conseguenze

- Servono `PERPLEXITY_API_KEY` (obbligatoria per la ricerca) e, facoltativamente, `DEEPSEEK_API_KEY` per l'estrazione strutturata.
- Il budget globale (3 USD su 24 ore) ora copre ricerca, estrazione e sintesi.
- I test automatici usano provider finti; la qualità reale va misurata con poche ricerche controllate (vedi `docs/deployment-security.md`).
