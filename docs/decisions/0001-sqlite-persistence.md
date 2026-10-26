# 0001 — SQLite al posto dell'archivio Excel

**Stato**: accettata (ottobre 2026)

**Contesto.** L'archivio Excel veniva letto e riscritto per intero in nove punti del codice, senza transazioni né stato dei job. La riprogettazione richiede analisi persistite e riapribili identiche, job con stato, paginazione e ripresa dopo il ricaricamento. Nella copia locale non esisteva alcun file Excel da migrare.

**Decisione.** SQLite tramite `sqlite3` della libreria standard, con un unico modulo di accesso (`linkedia/storage/store.py`). I risultati delle analisi sono JSON immutabili con la versione del metodo.

**Conseguenze.** Nessun servizio esterno da gestire; un solo processo scrittore in produzione (Gunicorn con un worker). Se in futuro servissero più istanze, il modulo di storage è l'unico punto da sostituire (per esempio con PostgreSQL).
