# Pubblicazione, sicurezza e controllo della spesa

Stato di riferimento: 28 ottobre 2026. URL pubblico: <https://linked-intelligent-analyst.it>.

## 1. Architettura di produzione

```
visitatore ──HTTPS──▶ edge Railway (TLS, certificato gestito) ──▶ 1 container: gunicorn (1 worker, 8 thread)
                                                                   ├─ Flask: /api/* + frontend compilato
                                                                   ├─ job in background (1 thread)
                                                                   └─ SQLite su volume persistente /data
DNS: Hostinger (nameserver *.dns-parking.com) → record verso Railway
```

- Un solo progetto Railway dedicato (**LiA**), un servizio collegato a `Marco17Cherubini/Linked-IA`, branch `main`, build da `Dockerfile` (`railway.json`).
- Un solo processo e una sola replica: coerente con SQLite e con i job in memoria. Con un volume, Railway non sovrappone due deployment: durante un redeploy c'è un breve fermo.
- Avvio (`docker-entrypoint.sh`): sistema i permessi del volume, passa all'utente `lia`, esegue `python -m linkedia init` (schema, catalogo, analisi dimostrative mancanti, copia di sicurezza; idempotente, nessuna cancellazione, nessuna IA), poi `gunicorn` su `0.0.0.0:$PORT`.
- Frontend e API sullo stesso dominio: nessun CORS.

## 2. Accesso

| Aspetto | Implementazione |
|---|---|
| Password | solo l'hash Argon2id in `LIA_OPERATOR_PASSWORD_HASH` (libreria `argon2-cffi`) |
| Sessione | token casuale di 256 bit nel cookie `__Host-lia_session` (Secure, HttpOnly, SameSite=Strict, Path=/); nel database solo lo SHA-256 |
| Scadenza | assoluta, 8 ore (`LIA_SESSION_HOURS`) |
| Logout | elimina la riga della sessione: il cookie copiato non vale più |
| CSRF | token per sessione nell'intestazione `X-CSRF-Token` + controllo di `Origin`/`Sec-Fetch-Site`; il login accetta solo JSON con origine uguale |
| Tentativi | 5 falliti per client e 20 complessivi ogni 15 minuti, registrati in SQLite (sopravvivono ai riavvii); il client è un HMAC dell'IP con un segreto dell'istanza |
| Errori | messaggi generici (`invalid_credentials`, `unauthorized`, `csrf`), nessun dettaglio interno |
| Configurazione assente | senza hash: login 503 e tutte le operazioni riservate 503, prima di qualunque accodamento |
| Browser | nessuna credenziale in localStorage/sessionStorage; il token CSRF vive solo in memoria |
| Percorsi legacy | `LIA_ADMIN_TOKEN` e l'intestazione `Authorization: Bearer` sono ignorati; un test verifica che ogni rotta `/api` non-GET richieda la sessione |
| Job | il job ricontrolla la validità della sessione al momento dell'esecuzione |

### Cambio password e revoca delle sessioni

1. Generare il nuovo hash senza scrivere la password in argomenti o file:
   ```bash
   python -m linkedia hash-password
   ```
2. Nel servizio Railway, scheda *Variables*, sostituire `LIA_OPERATOR_PASSWORD_HASH` (il redeploy parte da solo). Tutte le sessioni create con il vecchio hash diventano invalide.
3. Per chiudere le sessioni senza cambiare password: incrementare `LIA_SESSION_EPOCH`, oppure `railway ssh` e `python -m linkedia revoke-sessions`.

## 3. Budget e chiamate a pagamento

Provider a pagamento: **Perplexity Search API** (ricerca notizie, 0,005 USD per richiesta) e **DeepSeek** (estrazione facoltativa delle schede evento e sintesi IA). Yahoo Finance (prezzi) è gratuito ma esterno: richiede comunque la sessione e conta come job esterno. Tutte le chiamate a pagamento passano da `linkedia/services/paid_calls.py`.

| Regola | Valore iniziale | Variabile |
|---|---|---|
| Budget globale | 3,00 USD sulle ultime 24 ore (finestra mobile) | `LIA_API_BUDGET_USD`, `LIA_API_BUDGET_WINDOW_HOURS` |
| Job esterni simultanei | 1 (controllo e inserimento nella stessa transazione) | — |
| Pausa dopo un rifiuto | 60 minuti, persistente | `LIA_API_BLOCK_MINUTES` |
| Sintesi per 24 ore | 20 | `LIA_AI_DAILY_LIMIT` |
| Modelli ammessi | `deepseek-flash`, `deepseek-v4-pro` (prezzi di picco verificati il 2026-10-28), Perplexity `search` (prezzo per richiesta) | `DEEPSEEK_MODEL` |
| Costo massimo per ricerca | 0,05 USD (2 richieste × 2 tentativi + estrazione) | `LIA_NEWS_SEARCH_MAX_USD` |
| Riuso di ricerche identiche | 6 ore (date degli ultimi 30 giorni), 30 giorni (date storiche) | — |

Per ogni tentativo (anche i retry):

1. modello e prezzo dalla tabella `PRICING` (`linkedia/services/budget.py`); modello assente → nessuna chiamata;
2. limiti: testo inviato ≤ 48 000 byte, `max_tokens` = 900, modalità *thinking* disattivata;
3. riserva = (byte inviati + 64) × prezzo input cache-miss + 900 × prezzo output, arrotondata per eccesso, in micro-USD interi;
4. prenotazione in una transazione `BEGIN IMMEDIATE`: se riservato + confermato + incerto delle ultime 24 ore + riserva > budget, nessuna chiamata e blocco di 60 minuti;
5. la richiesta parte solo dopo la prenotazione riuscita;
6. alla risposta si calcola il costo dall'utilizzo dichiarato (cache hit/miss, output e token di ragionamento sommati per prudenza); senza utilizzo leggibile si conferma l'intera riserva;
7. esiti: `confirmed` (costo reale), `released` (solo HTTP 4xx o connessione mai stabilita: non elaborato), `uncertain` (timeout, 5xx, risposta illeggibile: la riserva resta impegnata e non si ripete la chiamata).

Al riavvio le riserve rimaste `reserved` diventano `uncertain`: non vengono mai liberate automaticamente; escono dal conteggio solo quando la loro data supera le 24 ore. Il blocco (`budget_state.blocked_until`) e il registro sono nel database sul volume: sopravvivono a riavvio, redeploy, logout e cambio di browser. Il budget è uno solo per l'istanza, indipendente da sessione e IP. Se il database non è raggiungibile la prenotazione fallisce e la chiamata non parte.

Quando cooldown e finestra lo consentono, il primo tentativo successivo riparte normalmente; se il budget delle 24 ore è ancora esaurito, il rifiuto avvia un nuovo blocco di 60 minuti (nessun azzeramento automatico dopo un'ora). L'operatore vede in `/new` e nella scheda «Sintesi IA» confermato, riservato, incerto, residuo e il momento del possibile sblocco; l'interfaccia non ripete le richieste da sola.

### Limiti della protezione applicativa

- Dipende dalla correttezza della tabella prezzi e dall'utilizzo dichiarato dal provider: se DeepSeek cambia tariffe, aggiornare `PRICING` (data di verifica inclusa) prima di riattivare la sintesi. Si usano sempre le tariffe di picco.
- Il calcolo del tetto in ingresso presume che un token copra almeno un byte UTF-8.
- Non protegge da un uso della stessa chiave API fuori da LiA.
- **Perplexity**: la documentazione pubblica descrive crediti acquistati e livelli d'uso, non tetti di spesa per chiave né ricariche automatiche. Tenere un credito basso e verificare nella console che la ricarica automatica sia disattivata.
- **Limite esterno indipendente**: DeepSeek funziona a credito prepagato (termini del servizio); la documentazione pubblica non descrive tetti per chiave né ricariche automatiche. La protezione esterna efficace è mantenere sul conto un credito basso e una chiave usata solo da LiA. Va verificato dal titolare nella console DeepSeek che non sia attiva alcuna ricarica automatica.

### Costi separati

| Voce | Natura | Stima |
|---|---|---|
| Chiamate IA (DeepSeek) | consumo, coperto dal budget applicativo | ≤ 3 USD ogni 24 ore per costruzione; con i 35 casi attuali (5–9,5 KB di dati) la riserva per sintesi è ≈ 0,003–0,004 USD, il tetto teorico a 48 KB ≈ 0,016 USD |
| Hosting Railway | abbonamento del piano + consumo di CPU, RAM, rete e volume | vedi sezione 6 |
| Dominio Hostinger | canone annuale del registrar | secondo il contratto Hostinger |

Il budget applicativo non limita i costi di hosting né il canone del dominio.

## 4. Dati, pubblico e privato

- Pubblici: solo gli eventi con `public = 1`, cioè il catalogo curato (`"public": true` in `linkedia/data/events.json`). Gli eventi creati dall'operatore nascono privati; `python -m linkedia set-public ID` li pubblica esplicitamente.
- Senza sessione elenchi e dettagli escludono i privati (404 sul dettaglio). Le analisi di un caso pubblico usano come precedenti solo casi pubblici.
- Conservazione: sessioni fino a scadenza o logout (residui rimossi a ogni login e avvio), tentativi di accesso 24 ore, registro spese senza dati personali, casi finché utili. Nessun dato storico è stato cancellato nella migrazione.
- Informative: `/privacy` e `/cookie` descrivono esattamente un cookie tecnico, nessuno storage persistente, nessuna risorsa esterna. I dati del titolare arrivano da `LIA_CONTROLLER_NAME` e `LIA_CONTROLLER_EMAIL`; senza questi valori le pagine si dichiarano non definitive.

### Punti che richiedono una valutazione legale

- Basi giuridiche indicate (legittimo interesse per registri e accesso) e bilanciamento.
- Trasferimenti: Railway (USA, DPA del fornitore) e DeepSeek (Cina, senza decisione di adeguatezza; LiA non invia dati personali per regola d'uso).
- Tempi di conservazione dei registri HTTP della piattaforma, che dipendono dal piano Railway.
- Eventuali obblighi informativi ulteriori legati all'uso di IA generativa.

Queste pagine non costituiscono una certificazione di conformità.

## 5. Sicurezza applicativa (stato)

- Autorizzazione lato server su ogni operazione riservata, controllata prima di accodare job o contattare provider.
- SQL parametrizzato (gli unici frammenti dinamici sono nomi di colonna costanti).
- Corpo JSON obbligatorio, massimo 64 KB; campi con lunghezze massime; URL delle fonti solo `http`/`https` e mai scaricati dal server (nessun rischio SSRF).
- Output inserito nel DOM da React (nessun `dangerouslySetInnerHTML`).
- Timeout su ogni richiesta esterna; retry limitati (prezzi: 2 con backoff; IA: 1, solo se certamente non fatturato e con nuova riserva).
- Debug disattivato, errori pubblici senza traceback, log senza password, token o corpi delle richieste, nessun access log applicativo.
- Intestazioni: CSP restrittiva, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP, HSTS (1 anno, senza `includeSubDomains`), `Vary: Cookie`, `Cache-Control: no-store` sulle API.
- `ProxyFix` con un solo hop fidato (`LIA_PROXY_HOPS=1`), così IP e schema arrivano dal proxy di Railway e non dal client.
- `www.` → dominio principale con redirect 301 applicativo (`LIA_CANONICAL_HOST`).
- `/api/health` restituisce solo `{status}`.

## 6. Railway

| Elemento | Valore |
|---|---|
| Progetto | `LiA` (dedicato) |
| Servizio | `lia-web`, sorgente `Marco17Cherubini/Linked-IA` @ `main` |
| Regione | Europe West (Amsterdam) |
| Volume | montato su `/data` (database, sessioni, budget, copie locali) |
| Health check | `/api/health`, timeout 300 s |
| Variabili | `LIA_OPERATOR_PASSWORD_HASH` (segreto), `LIA_PROXY_HOPS=1`, `LIA_CANONICAL_HOST`, `LIA_API_BUDGET_USD=3.00`, `LIA_CONTROLLER_*`; `DEEPSEEK_API_KEY` solo se il titolare vuole attivare le sintesi |

Costo stimato del servizio (prezzi Railway: RAM 10 USD/GB/mese, CPU 20 USD/vCPU/mese, volume 0,15 USD/GB/mese): con ~150 MB di RAM e CPU quasi inattiva circa 1,5–2,5 USD/mese di consumo, compresi nei 5 USD di utilizzo inclusi nel piano Hobby solo se gli altri progetti dello stesso account non li esauriscono.

## 7. DNS e HTTPS

I nameserver autorevoli sono quelli di Hostinger. Si modificano solo i record richiesti da Railway per `linked-intelligent-analyst.it` e `www` (più eventuali TXT di verifica); gli altri record restano invariati. I valori precedenti sono registrati nella sezione 9. Railway emette e rinnova i certificati; non serve SSL a pagamento.

## 8. Backup e ripristino

- A ogni avvio `init` salva una copia coerente (API di backup SQLite) in `/data/backups`, mantenendo le ultime 7. Manuale: `railway ssh` → `python -m linkedia backup`.
- Backup del volume Railway (scheda *Backups* del servizio): programmazione giornaliera (conservata 6 giorni) e settimanale (27 giorni). Il ripristino crea un nuovo volume e va confermato con *Deploy*.
- Ripristino da copia locale: fermare il servizio, sostituire `/data/lia.sqlite3` con la copia (e rimuovere `-wal`/`-shm`), riavviare.
- Un rollback del codice non ripristina i dati: lo schema v2 resta compatibile in avanti; tornare a una versione precedente alla v2 richiede di ripristinare anche un backup precedente alla migrazione.

## 9. Registro delle operazioni di pubblicazione (28 ottobre 2026)

**Railway** — progetto `LiA` (`42a8dd60-5098-48ab-860c-58e1e6bba85f`), ambiente `production`, servizio `lia-web` (`409f5cc9-ab9d-4b42-84a4-4256ec955eef`), regione `europe-west4-drams3a`, volume `lia-data` (5 GB) su `/data`, dominio tecnico `lia-web-production-cb95.up.railway.app`. Nessuna modifica ai progetti Lev Space, Lev Space.it, Ellebi-Service.

**DNS Hostinger** (nameserver `cosmos.dns-parking.com`, `nova.dns-parking.com`, invariati). Zona prima della modifica:

| Tipo | Nome | Valore | TTL |
|---|---|---|---|
| A | @ | 2.57.91.91 (parcheggio Hostinger) | 50 |
| CNAME | www | linked-intelligent-analyst.it | 300 |

Zona dopo la modifica (nessun record MX o di altri sottodomini esisteva né è stato toccato):

| Tipo | Nome | Valore | TTL |
|---|---|---|---|
| ALIAS (inserito come CNAME @) | @ | 2iq9ad3u.up.railway.app | 300 |
| CNAME | www | byepyf29.up.railway.app | 300 |
| TXT | _railway-verify | railway-verify=… (valore fornito da Railway per il dominio principale) | 300 |
| TXT | _railway-verify.www | railway-verify=… (valore fornito da Railway per www) | 300 |

L'`A @` di parcheggio è stato rimosso perché Hostinger non consente un ALIAS insieme a un record A sullo stesso nome. Ripristino: eliminare l'ALIAS e ricreare `A @ 2.57.91.91`, riportare `www` a `linked-intelligent-analyst.it`.

Il dominio `www` è servito dallo stesso servizio; l'applicazione risponde con 301 verso `https://linked-intelligent-analyst.it` mantenendo percorso e query.

## 10. Piano dei task

| ID | Obiettivo | File/servizi | Dipendenze | Rischio | Difficoltà | Effort | Verifica |
|---|---|---|---|---|---|---|---|
| T1 | Inventario repo, accessi, DNS, consumi esterni | repo, Railway, DNS | — | basso | D1 | low | note di diagnosi |
| T2 | Accesso: hash, sessioni, CSRF, limiti | `services/auth.py`, `api/routes.py`, `store.py` | T1 | alto | D3 | high | `tests/test_security.py` |
| T3 | Contabilità e blocco della spesa | `services/budget.py`, `summary.py`, `llm.py` | T1 | alto | D5 | max | `tests/test_budget.py` |
| T4 | Job: esclusività e ricontrollo | `services/analysis.py`, `summary.py` | T2 | medio | D4 | xhigh | test job/sessione |
| T5 | Pubblico/privato e precedenti | `store.py`, `routes.py`, `events.json` | T1 | medio | D3 | high | test isolamento |
| T6 | Hardening HTTP e proxy | `api/app.py` | T2 | medio | D2 | medium | test intestazioni |
| T7 | Frontend: login, budget, informative | `frontend/src` | T2, T3 | medio | D3 | high | vitest + browser |
| T8 | Docker, avvio, backup | `Dockerfile`, `docker-entrypoint.sh`, `cli.py` | T5 | medio | D4 | xhigh | `tests/test_cli.py`, build Railway |
| T9 | Railway: progetto, volume, variabili, deploy | Railway | T8 | alto | D4 | xhigh | URL Railway |
| T10 | DNS Hostinger e HTTPS | Hostinger, Railway | T9 | alto | D4 | xhigh | resolver, TLS, redirect |
| T11 | Documentazione e revisione finale | `docs/`, README | tutti | basso | D1/D5 | low/max | suite completa |

L'effort indicato è una classificazione di pianificazione: la sessione è stata eseguita con un unico livello di ragionamento.

## 11. Limiti noti

- Un attaccante può esaurire i 20 tentativi globali e impedire per 15 minuti anche l'accesso dell'operatore (scelta deliberata: il limite globale impedisce attacchi distribuiti sulla password).
- Con una sola replica, un riavvio o un redeploy interrompe il sito per alcuni secondi; i job in corso vengono marcati `interrupted`.
- I prezzi Yahoo provengono da un endpoint pubblico non ufficiale: può cambiare o limitare le richieste dai data center.
