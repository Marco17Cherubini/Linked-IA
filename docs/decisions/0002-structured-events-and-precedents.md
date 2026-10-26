# 0002 — Eventi strutturati e precedenti con cutoff

**Stato**: accettata (ottobre 2026)

**Contesto.** La versione precedente raccoglieva notizie da feed RSS (in parte dismessi) e scraping con selettori obsoleti, chiedeva a un LLM un "report_nesso" testuale e confrontava i report per parole in comune su tutto l'archivio, inclusi eventi successivi e l'articolo stesso. L'indicatore `momentum7` usava il prezzo a T+7 come input. Nessun risultato era riproducibile.

**Decisione.**
- L'evento è un'entità strutturata: data, orario con fuso e precisione, categoria, etichette, fonti.
- La seduta base è determinata per mercato con una convenzione esplicita; input al cutoff ed esiti futuri sono separati nel modello dati e nell'API.
- I precedenti si scelgono per categoria ed etichette, e solo se il loro esito a 20 sedute era osservabile alla seduta base.
- Le statistiche sono descrittive, con numerosità minime, e non vengono presentate come probabilità.

**Conseguenze.** Il metodo è deterministico e verificabile, ma la pertinenza dei precedenti dipende dalla qualità delle etichette e dalla dimensione del catalogo. Similarità semantica (embedding) e modelli previsionali sono fuori ambito finché non esiste un protocollo di validazione.
