# LiA — Linked Intelligent Analyst

**Less time and less guesswork when a geopolitical shock hits: LiA shows how the markets moved around a documented event, and after similar events in the past.**

[![CI](https://github.com/Marco17Cherubini/Linked-IA/actions/workflows/ci.yml/badge.svg)](https://github.com/Marco17Cherubini/Linked-IA/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-%3E%3D3.11-3776AB)
![Node.js](https://img.shields.io/badge/node-%3E%3D20-339933)

> The user interface is in Italian: LiA was developed for a thesis at the University of Eastern Piedmont (UNIUPO).

---

## The story

### Context

Financial advisors face a time gap. Following geopolitics continuously — wars, sanctions, central-bank moves, attacks — takes hours that the job does not leave, and reading a shock under pressure exposes the decision to bias and error. Yet the link between geopolitics and markets is well documented: the **International Monetary Fund** finds that stock prices fall noticeably during major geopolitical risk events — about **1 percentage point a month on average**, about **2.5 points in emerging markets**, and more for military conflicts — and that these risks are hard to price because they are rare and their duration is uncertain ([IMF, 2025](https://www.imf.org/en/blogs/articles/2025/04/14/how-rising-geopolitical-risks-weigh-on-asset-prices)).

LiA was born as the project of a thesis at the University of Eastern Piedmont (UNIUPO) to close that gap: take the IMF's reading of geopolitical shocks and turn it into a tool that shows, event by event, what the markets actually did.

### The main point

**Reduce the uncertainty of the decision and the time it takes**, by giving the advisor the market facts of a shock — and its historical precedents — in one screen instead of hours of reading.

LiA is a web application with a Python back end and a React front end:

- a **catalogue of documented events** — date, time with time zone, category, tags and sources — that analysts can extend;
- **daily prices of five indices** (S&P 500, Nasdaq Composite, DAX 40, FTSE 100, Nikkei 225) downloaded for free from Yahoo Finance;
- a **deterministic engine** that finds, for each market, the last close before the event, measures what happened after 1, 5 and 20 sessions and selects comparable precedents whose outcome was already known on that date;
- an **optional AI summary**: with a DeepSeek API key, an authorised analyst can ask for a written reading of the computed data, never generated automatically.

Exploring a case takes three steps: open an event, look at the market around it, compare it with its precedents.

| 1. Open an event                                                                                 | 2. Read the market around it                                                                                   | 3. Compare with precedents                                                                          |
| ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| ![Home page with the demo case and its S&P 500 chart in base 100](docs/images/01-home.jpg) | ![FTSE 100 around the invasion of Ukraine: base session, event marker, indicators at cutoff](docs/images/02-workspace-mercato.jpg) | ![DAX: the event against five precedents, one highlighted](docs/images/03-precedenti.jpg) |

### Results & case studies

The thesis tested LiA on three shocks of different nature. All figures below are produced by the current version of LiA and match the historical closes.

> **How the dates line up.** LiA measures every move from **the last close before the event**, so each case has two dates: the event itself and the reference close of the previous trading session (for the invasion of Ukraine: event on 24 February 2022, reference close on 23 February). The first move shown — "first session after the event" — is the market's reaction **on the event day** — or on the first day the market traded after it — compared with that close. In the charts the amber dashed line marks the event: what is on its left was known before, what is on its right is the reaction. After 11 September, for example, Wall Street's first session after the event is the reopening on 17 September.

| Case (event date) | Reference close (last before the event) | First session after the event | After 20 sessions | Precedents in the catalogue |
| --- | --- | --- | --- | --- |
| **Russia invades Ukraine** — 24 Feb 2022, geopolitical | 23 Feb 2022 | DAX **−3.96%**, FTSE 100 **−3.88%**, Nikkei **−1.81%**; S&P 500 **+1.50%** | DAX −2.38%, S&P 500 +5.46% | 5 |
| **Lehman Brothers files for bankruptcy** — 15 Sep 2008, financial | 12 Sep 2008 | S&P 500 **−4.71%**, FTSE 100 −3.92%, DAX −2.74%, Nikkei −4.95% | S&P 500 **−28.16%**, every index between −22% and −28% | 0 |
| **11 September attacks** — 11 Sep 2001, terrorism | 10 Sep 2001 | DAX **−8.49%** the same afternoon; S&P 500 **−4.92%** at the reopening on 17 Sep | S&P 500 −11.60% after 5 sessions | 0 |

| 24/02/2022 — Russia invades Ukraine (DAX 40) | 15/09/2008 — Lehman Brothers (S&P 500) | 11/09/2001 — September 11 attacks (S&P 500) |
| --- | --- | --- |
| ![DAX 40 around the invasion of Ukraine: −3.96% in the first session, −2.38% after 20](docs/images/10-case-ukraine.jpg) | ![S&P 500 around the Lehman bankruptcy: −4.71% in the first session, −28.16% after 20](docs/images/08-case-lehman.jpg) | ![S&P 500 around 11 September: closed until the 17th, −4.92% at the reopening, −11.60% after 5 sessions](docs/images/11-case-sept11-chart.jpg) |

**Ukraine — a geopolitical shock read correctly.** The blow hit hardest the markets closest to the conflict: European indices lost about 4% in the first session while Wall Street recovered within the day. The pattern is the one the IMF describes for military conflicts, and LiA can place it next to five earlier geopolitical events (Crimea 2014, Iraq 2003, Soleimani 2020, the 2017 North Korean test, the 2020 oil price war).

**Lehman — a financial shock recognised as different.** The first-session falls already exceed the range the IMF reports for geopolitical shocks, and after 20 sessions all five indices are down 22–28%: the profile of a systemic banking crisis, the kind of systemic banking crisis catalogued in the IMF database by [Laeven & Valencia (2012)](https://www.imf.org/en/Publications/WP/Issues/2016/12/31/Systemic-Banking-Crises-Database-An-Update-26015). The thesis used exactly this contrast to show that LiA separates an external geopolitical shock from an internal financial one.

**11 September — where the model meets a black swan.** US markets stayed closed until 17 September, the longest closure since 1933. The thesis prototype read only the data of the day itself and **failed**: it saw contained moves where there was a crash. The current version anchors the measure on the last close before the attack and reports the −4.92% at the reopening, flagging the closure. But it still has **no precedent to compare it with**: the statistics stay empty, because nothing like it had happened before. However well LiA reworks the data, an event without history remains outside what it can interpret — that is the limit the case was chosen to expose.

![11 September, quality panel: market closed for six days and no usable precedents](docs/images/09-case-sept11.jpg)

### From the thesis prototype to LiA 2.0

The prototype described in the thesis scraped news, asked a language model to write a link between each article and the prices, and compared those texts word by word. A review showed that some indicators used prices from after the event, that "patterns" were searched among later events too, and that provider errors silently became empty results. LiA 2.0 keeps the idea and the case studies but rebuilds the method on checkable data: structured events, an explicit time convention, precedents with no hindsight and statistics that declare their sample size. The original pipeline is documented in [docs/history/](docs/history/).

---

## What makes it different

LiA is not a news feed or a price chart: every feature exists to make the link between an event and the markets readable and honest.

### The base session: time zones taken seriously

An event at 22:00 in New York happens the next morning in Tokyo, before the close. For every index LiA finds the **last session that closed before the event**, using each exchange's time zone and closing time (including the Tokyo change to 15:30 in November 2024). When the time is unknown it applies a **cautious convention** — the last session before the event date — and says so on screen.

### Known then vs. happened later

Inputs available at the cutoff (the price path up to the base session and indicators such as 20-session volatility or distance from the 60-session high) are kept apart from outcomes (returns after 1, 5 and 20 sessions). The **"Al cutoff" view** hides everything after the event: the server does not even send it.

### Precedents without hindsight

Precedents share the category or at least two tags with the event, are ranked by a declared score, and are admitted **only if their 20-session outcome was observable on the event's base session**. Each one opens with its date, the reason it was selected, its returns and its sources.

### Statistics that admit their size

Median and quartiles appear only when the sample is large enough (3 and 5 cases). Small samples are drawn **case by case**, larger ones as a histogram. The share of rises is labelled as an **observed frequency, not a probability**, and no band is drawn as if it were a forecast interval.

### Every chart has a text version

Each chart comes with a written summary and a data table, definitions are one click away next to every metric, and the charts can be explored with the keyboard. Light and dark themes, reduced motion and phone layouts are supported.

![Phone layout of the analysis workspace](docs/images/07-mobile.jpg)

### Analyses you can reopen and share

Every analysis is saved with the method version and a snapshot of the event, so **reopening it shows exactly the same result**. Market, view, window, horizon and selected precedents live in the URL. Jobs keep running on the server if the page is reloaded.

### AI only when asked

An authorised analyst can request a written summary. It costs money, so it needs **explicit confirmation**, runs once per analysis within a daily limit, receives only the computed data and must answer with a fixed, validated structure. Browsing, filtering or switching markets never calls the model.

### Searchable archive

All saved analyses can be filtered by text, category, status and date, with pagination.

![Archive filtered on financial crises](docs/images/06-archivio-scuro.jpg)

---

## Under the hood

### Tech stack

| Layer       | Choice                                         | Why                                                                                     |
| ----------- | ---------------------------------------------- | --------------------------------------------------------------------------------------- |
| Server      | Python + Flask                                 | Small API over a deterministic domain layer; the same services serve the API and the CLI |
| Database    | SQLite (standard library `sqlite3`)            | One file, transactions, job state that survives restarts; no service to run             |
| Market data | Yahoo Finance public chart endpoint            | Free daily prices for the five indices; timeouts, limited retries, validation, cooldown |
| AI          | DeepSeek (OpenAI-compatible, JSON mode)        | Optional summary, only on explicit request                                              |
| Frontend    | React 18 + Vite + React Router                 | Interactive workspace with state in the URL                                             |
| Charts      | Recharts 3                                     | One declarative SVG library for line, dot and histogram charts                          |
| Tests       | pytest (network blocked) + Vitest              | Offline, no keys, no costs                                                              |

### Architecture

```
frontend/ (React)                         linkedia/
  pages/          home, archive,            api/          Flask routes, errors, security headers
                  methodology, new          cli.py        seed · analyze · events · serve
  features/       workspace, charts,        services/     analyses, AI summary, background jobs
    analysis/     panels, job polling       domain/       markets, sessions, indicators,
  components/     controls, tabs, states                  precedents, statistics (pure, no I/O)
  styles/         tokens → base →           providers/    Yahoo prices, DeepSeek (timeouts, retries)
                  components → pages        storage/      SQLite: events, prices, analyses
        fetch JSON  ─────────────────▶
```

Routes only translate HTTP; the method lives in `domain/`, which has no I/O. Errors have stable codes (400/403/404/409/502/503) and a message for the user; diagnostic details stay in the server logs.

### Quality and security

- **47 offline backend tests** with the network blocked: event-to-session convention across time zones, indicators, minimum sample sizes, precedent cutoff, provider failures, API contracts, persistence, restart recovery and cost controls on the AI summary. **14 frontend tests** cover formatting, chart scales, form payloads and the as-of view.
- An optional smoke test checks the real price provider against a known close.
- No secrets in the source code; analyst token compared in constant time and never put in URLs; debug off by default; Content Security Policy; request size limit.
- GitHub Actions runs lint, tests and the production build on every push (Python 3.11 and 3.12, Node 22).

---

## Getting started

Requirements: **Python 3.11 or newer** and **Node.js 20 or newer**.

```bash
git clone https://github.com/Marco17Cherubini/Linked-IA.git
cd Linked-IA
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Linux/macOS: .venv/bin/python
cd frontend && npm ci && npm run build && cd ..
```

Load the catalogue and start the app:

```bash
.venv/Scripts/python -m linkedia seed    # downloads free prices, computes the 34 analyses
.venv/Scripts/python -m linkedia serve   # http://127.0.0.1:5000
```

No command calls a paid service. Without any configuration LiA runs in read-only mode.

### Useful commands

| Command                               | What it does                                                   |
| ------------------------------------- | -------------------------------------------------------------- |
| `python -m linkedia seed`             | Import the curated catalogue, sync prices, compute analyses    |
| `python -m linkedia analyze <id>`     | Recompute the analysis of one event                            |
| `python -m linkedia events`           | List the events in the database                                |
| `python -m linkedia serve`            | Development server on 127.0.0.1:5000                           |
| `python -m pytest` / `ruff check .`   | Offline tests and lint                                         |
| `python -m pytest -m external`        | Smoke test against the real price provider                     |
| `npm run dev` (in `frontend/`)        | Frontend with hot reload on port 5173, proxying `/api`         |
| `npm test` / `npm run build`          | Frontend tests and production build                            |

### Configuration

Copy `.env.example` to `.env`. Every variable is optional.

| Variable              | Default                  | Purpose                                                           |
| --------------------- | ------------------------ | ----------------------------------------------------------------- |
| `LIA_ADMIN_TOKEN`     | —                        | Enables creating analyses and requesting AI summaries             |
| `DEEPSEEK_API_KEY`    | —                        | Enables the AI summary (paid), together with the token            |
| `DEEPSEEK_MODEL`      | `deepseek-chat`          | Model used for the summary                                        |
| `LIA_AI_DAILY_LIMIT`  | `20`                     | Maximum summaries in 24 hours                                     |
| `LIA_DATABASE_PATH`   | `instance/lia.sqlite3`   | SQLite file (relative paths start from the project root)          |
| `LIA_FRONTEND_DIST`   | `frontend/dist`          | Built frontend served by Flask                                    |
| `LIA_FEATURED_EVENT`  | `russia-invades-ukraine-2022` | Demo case on the home page                                  |
| `LIA_HTTP_TIMEOUT`    | `20`                     | Timeout in seconds for external providers                         |
| `LIA_LOG_LEVEL`       | `INFO`                   | Log level                                                         |
| `LIA_DEBUG`           | `false`                  | Local development only                                            |

### Deployment

The `Dockerfile` builds the frontend and runs Gunicorn as **one process** (background jobs live in the process, their state in SQLite). Mount a persistent volume on `/data`, set a strong `LIA_ADMIN_TOKEN` and serve the app behind HTTPS:

```bash
docker build -t lia .
docker run -p 8000:8000 -v lia-data:/data --env-file .env lia
docker run --rm -v lia-data:/data lia python -m linkedia seed
```

The image has not been run yet: it was written in an environment without Docker.

---

## Development

Before pushing, run `ruff check .`, `python -m pytest` and, in `frontend/`, `npm test` and `npm run build` — the same checks run in CI.

- **Domain**: `linkedia/domain/` is pure — no network, files or imports from the rest of the package. Changing a formula, a time convention or the precedent rules means bumping `METHOD_VERSION` and updating the Methodology page and the tests.
- **Errors**: provider failures are `ProviderUnavailable` and are never turned into empty lists or zeros; missing values stay `null` with a reason.
- **Frontend**: view state lives in the URL (`useUrlState`); definitions shared by charts and the Methodology page are in `src/content/glossary.js`; colours come from tokens so both themes keep their contrast.
- **AI**: paid calls happen only through `POST /api/analyses/:id/summary` with `confirm_cost`, never in tests or in `seed`.
- User-facing text and code comments are in Italian. Architecture and API contracts are in [docs/architecture.md](docs/architecture.md), decisions in [docs/decisions/](docs/decisions/).

## Known limitations

- **Small samples**: the catalogue is curated and small, so each event has only a handful of precedents. The interface says so, but the numbers describe a few cases, not a general law.
- **Correlation, not causation**: other news moves markets in the same days as the event.
- **Unofficial price source**: the Yahoo endpoint is public but not an official API; gaps and errors are flagged, never filled.
- **Reference sources**: catalogue sources are encyclopedia entries and official statements, not original reports from the time.
- **Market hours**: early closes and historical changes of closing time (except Tokyo 2024) are not modelled; approximate event times can shift the base session when they fall near a close.
- **No out-of-sample validation**: semantic similarity and forecasting models are deliberately out of scope until the method can be evaluated.

## Project structure

```
linkedia/      Python package: domain, providers, storage, services, api, cli, data/events.json
frontend/      React app: pages, features/analysis, components, styles, tests
tests/         pytest suites (offline) and the optional external smoke test
docs/          architecture, decisions, refactoring plan, images, history of the first prototype
```

## Author

Designed and built by **Marco Cherubini** — [github.com/Marco17Cherubini](https://github.com/Marco17Cherubini).

## License

No license has been chosen yet: all rights are reserved until a `LICENSE` file is added.
