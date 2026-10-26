# 0003 — Sintesi IA su richiesta, strutturata e validata

**Stato**: accettata (ottobre 2026)

**Contesto.** Nella versione precedente ogni analisi chiamava DeepSeek più volte (due volte per richiesta API), gli errori del modello venivano salvati come testo di analisi e il frontend riceveva testo libero.

**Decisione.** La sintesi è un job separato, avviato solo da un analista autenticato con conferma esplicita del costo, una volta per analisi (rigenerazione esplicita), entro un limite giornaliero. Il modello riceve solo i dati strutturati dell'analisi, risponde in JSON con schema fisso (titolo, osservazioni, interpretazione, limiti) e la risposta viene validata prima del salvataggio. Un errore resta un errore.

**Conseguenze.** Consultare, filtrare o cambiare vista non genera costi. Il caso dimostrativo può non avere una sintesi: l'interfaccia lo dichiara.
