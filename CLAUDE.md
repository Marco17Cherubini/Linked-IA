# CLAUDE.md

## Comandi
- Ambiente: `.venv/Scripts/python -m pip install -e ".[dev]"` (Linux/macOS: `.venv/bin/python`)
- Test backend (offline): `.venv/Scripts/python -m pytest` · lint: `.venv/Scripts/ruff check .`
- Smoke test reale e gratuito: `pytest -m external`
- Frontend: `cd frontend && npm ci && npm test && npm run build`
- Dati: `python -m linkedia seed` (prezzi gratuiti, nessuna IA) · server: `python -m linkedia serve`

## Convenzioni
- `linkedia/domain` è puro: niente I/O, rete o import dal resto del package.
- Gli errori dei provider sono `ProviderUnavailable`: mai convertirli in liste vuote, zero o "nessun evento".
- I dati mancanti restano `None`/null con il motivo; mai sostituirli con zero.
- Input al cutoff (`observed`) ed esiti futuri (`outcomes`) restano separati; la vista `as_of` omette gli esiti.
- Cambiare formule, convenzioni o criteri dei precedenti richiede di aggiornare `METHOD_VERSION`, la pagina Metodologia e i test.
- Le chiamate IA sono a pagamento: solo su richiesta esplicita con `confirm_cost`, mai durante test o seed.
- Testi dell'interfaccia e della documentazione in italiano; frequenze sempre "osservate", mai "probabilità".
- Non versionare `.env`, `instance/`, cache, `node_modules`, `frontend/dist`.

## Documenti
- Architettura e contratti API: `docs/architecture.md`
- Decisioni: `docs/decisions/`
- Piano, diagnosi e stato: `docs/refactoring-plan.md`
