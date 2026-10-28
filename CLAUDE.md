# CLAUDE.md

## Comandi
- Ambiente: `.venv/Scripts/python -m pip install -e ".[dev]"` (Linux/macOS: `.venv/bin/python`)
- Test backend (offline): `.venv/Scripts/python -m pytest` · lint: `.venv/Scripts/ruff check .`
- Smoke test reale e gratuito: `pytest -m external`
- Frontend: `cd frontend && npm ci && npm test && npm run build`
- Dati: `python -m linkedia seed` (prezzi gratuiti, nessuna IA) · server: `python -m linkedia serve`
- Locale con login: `LIA_OPERATOR_PASSWORD_HASH` da `python -m linkedia hash-password` e `LIA_COOKIE_SECURE=false`

## Convenzioni
- **La ricerca automatica delle notizie per data è una capacità centrale di LiA. Non può essere sostituita dall'inserimento manuale senza un'esplicita richiesta dell'utente** (`docs/decisions/0005-automatic-news-search.md`).
- Nella ricerca, URL, fonti e date vengono solo dai risultati del provider; il modello non li scrive. Data dell'evento ≠ data di pubblicazione ≠ data di recupero.
- `linkedia/domain` è puro: niente I/O, rete o import dal resto del package.
- Gli errori dei provider sono `ProviderUnavailable`: mai convertirli in liste vuote, zero o "nessun evento".
- I dati mancanti restano `None`/null con il motivo; mai sostituirli con zero.
- Input al cutoff (`observed`) ed esiti futuri (`outcomes`) restano separati; la vista `as_of` omette gli esiti.
- Cambiare formule, convenzioni o criteri dei precedenti richiede di aggiornare `METHOD_VERSION`, la pagina Metodologia e i test.
- Le chiamate IA sono a pagamento: solo su richiesta esplicita con `confirm_cost`, mai durante test, seed o init.
- Ogni chiamata a pagamento (anche i retry) passa da `run_paid` / `BudgetService.reserve()` prima di partire; un provider o modello senza prezzo in `PRICING` non si chiama.
- Ogni rotta che contatta servizi esterni usa `require_operator`; i dati privati (`public = 0`) non escono dalle rotte pubbliche.
- Produzione: Railway, un solo processo e una sola replica (SQLite sul volume `/data`). Mai password o chiavi in Git, log o bundle.
- Testi dell'interfaccia e della documentazione in italiano; frequenze sempre "osservate", mai "probabilità".
- Non versionare `.env`, `instance/`, cache, `node_modules`, `frontend/dist`.

## Documenti
- Architettura e contratti API: `docs/architecture.md`
- Decisioni: `docs/decisions/`
- Piano, diagnosi e stato: `docs/refactoring-plan.md`
- Pubblicazione, accesso, budget, backup, DNS: `docs/deployment-security.md`
