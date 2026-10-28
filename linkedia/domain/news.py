"""Ricerca di notizie per data: regole deterministiche, senza I/O.

Concetti tenuti separati:
- data dell'evento (ciò che si vuole analizzare);
- data di pubblicazione della fonte (dichiarata dal provider, può mancare);
- data di ultimo aggiornamento della fonte;
- momento del recupero da parte di LiA.

Due tipi di richiesta al provider:
- *contemporanea*: fonti pubblicate tra il primo giorno cercato e `CONTEMPORARY_LAG_DAYS` dopo
  l'ultimo. Sono le informazioni disponibili all'epoca (o subito dopo);
- *retrospettiva*: fonti pubblicate dal primo giorno cercato in poi, anche anni dopo, che citano
  la data. Possono contenere senno di poi e sono dichiarate come tali.

Il filtro temporale del provider non basta: ogni risultato viene ricontrollato qui sulla data di
pubblicazione dichiarata. Gli eventi non vengono mai scelti o ordinati in base ai rendimenti di
mercato successivi, che a questo punto non sono nemmeno noti.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .events import CATEGORIES

NORMALIZATION_VERSION = "news-v3"
MODES = ("auto", "contemporary", "retrospective")
MAX_RANGE_DAYS = 7
CONTEMPORARY_LAG_DAYS = 2
MAX_QUERIES_PER_REQUEST = 4
EARLIEST_DATE = date(1990, 1, 1)
MAX_FILTER_LENGTH = 80
MAX_TITLE = 160
MAX_DESCRIPTION = 600
MAX_SNIPPET = 500
CLUSTER_SIMILARITY = 0.5
# Due risultati descrivono lo stesso fatto se condividono abbastanza termini distintivi (nomi di
# persone, aziende, Paesi), esclusi quelli generici del linguaggio di mercato.
SHARED_TERMS_MIN = 3
# Tarata sulle ricerche reali del 28/10/2026: titolo ed estratto hanno in media 24 termini
# distintivi, e articoli diversi sullo stesso fatto ne condividono circa un quinto.
SHARED_TERMS_OVERLAP = 0.2
LANGUAGES = ("en", "it")
MIN_LATIN_SHARE = 0.6

_MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December")
_MONTHS_IT = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
              "settembre", "ottobre", "novembre", "dicembre")
_FILTER_TEXT = re.compile(r"^[\w\s.,'’\-&/()]+$", re.UNICODE)
_TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$|cmpid$|ocid$|smid$)", re.I)
_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "the a an and or of to in on at for with from by as is are was were be after before over into "
    "il lo la i gli le un una di da del della dei degli delle e ed o in su per con tra fra al alla "
    "news live update updates what how why says said new".split()
)

# Parole chiave → categoria. Servono solo a proporre una categoria quando non è disponibile
# un'estrazione strutturata; la scelta è sempre visibile e correggibile.
# Termini generici del linguaggio di mercato e di calendario: non distinguono un fatto da un altro.
_GENERIC = frozenset(
    "stock stocks market markets share shares equity equities index indices points pts percent per "
    "cent investor investors trading traders wall street dow jones nasdaq sensex nifty ftse dax "
    "nikkei close closed closes closing higher lower rise rises rose fall falls fell drop drops "
    "dropped gain gains loss losses day days week today yesterday tomorrow monday tuesday wednesday "
    "thursday friday saturday sunday january february march april june july august september "
    "october november december gennaio febbraio marzo aprile maggio giugno luglio agosto settembre "
    "ottobre novembre dicembre year years report reports highlights session sessions price prices "
    "global world asia asian europe european financial finance business economy economic "
    "notizie oggi borsa borse mercato mercati".split()
)

# Pagine indice e cronologie: elencano molti fatti, non sono un evento.
_INDEX_PAGE = re.compile(
    r"\b(on this day|this day in history|today in history|what happened on|headlines for|"
    r"top news|current events|daily (business )?briefing|news (summary|roundup|round-up)|"
    r"timeline|cronologia|accadde oggi|pagina \d+|page \d+|latest news|ultime notizie|"
    r"year in review|un anno di notizie|birthday|born on|horoscope|oroscopo)\b", re.I)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "geopolitical_conflict": ("war", "invasion", "invade", "military", "missile", "troops", "attack",
                              "guerra", "invasione", "militare", "conflict", "sanction", "sanzioni",
                              "russia", "ukraine", "ucraina", "putin", "kremlin", "nato"),
    "terrorism": ("terror", "terrorist", "bombing", "hijack", "attentato", "terrorismo"),
    "financial_crisis": ("bankruptcy", "collapse", "bailout", "default", "crisis", "fallimento",
                         "bank run", "insolvency", "crash", "lehman", "turmoil", "meltdown", "rescue",
                         "chapter 11", "bank failure", "aig", "merrill"),
    "monetary_policy": ("federal reserve", "fed ", "interest rate", "rate cut", "rate hike", "ecb",
                        "central bank", "bce", "tassi", "quantitative easing", "boj"),
    "political": ("election", "referendum", "president", "parliament", "elezioni", "governo",
                  "impeachment", "brexit", "resign"),
    "trade": ("tariff", "trade war", "dazi", "import", "export", "trade deal", "wto"),
    "pandemic": ("pandemic", "virus", "outbreak", "covid", "epidemic", "pandemia", "lockdown"),
    "natural_disaster": ("earthquake", "hurricane", "tsunami", "flood", "terremoto", "uragano",
                         "wildfire", "eruption"),
    "energy": ("oil", "opec", "gas price", "crude", "petrolio", "energy", "pipeline"),
}

FLAG_MESSAGES = {
    "single_source": "Una sola fonte indipendente.",
    "retrospective_only": "Solo fonti pubblicate dopo l'evento: possono contenere senno di poi.",
    "date_not_confirmed": "Le fonti non citano esplicitamente la data cercata.",
    "date_estimated": "Data dell'evento stimata dalla prima pubblicazione nell'intervallo.",
    "date_ambiguous": "Date di pubblicazione molto distanti tra loro: verificare la data dell'evento.",
    "missing_publication_date": "Alcune fonti non dichiarano la data di pubblicazione.",
    "snippet_only": "Verificato solo su estratti forniti dal motore di ricerca, non sull'articolo completo.",
    "syndicated_copies": "Alcune fonti sono copie dello stesso articolo: contate una volta sola.",
    "category_default": "Categoria non determinabile dalle fonti: proposta quella predefinita.",
}


@dataclass(frozen=True)
class SearchParams:
    start: date
    end: date
    mode: str = "auto"
    topic: str | None = None
    region: str | None = None
    category: str | None = None

    def to_dict(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "mode": self.mode,
                "topic": self.topic, "region": self.region, "category": self.category}

    def cache_key(self) -> str:
        """Chiave stabile: stessi parametri e stessa versione delle regole → stessa ricerca."""
        canonical = {**self.to_dict(), "topic": (self.topic or "").lower(),
                     "region": (self.region or "").lower(), "v": NORMALIZATION_VERSION}
        return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class RequestSpec:
    kind: str  # contemporary | retrospective
    queries: tuple[str, ...]
    published_after: date
    published_before: date | None


@dataclass(frozen=True)
class NewsResult:
    idx: int
    url: str
    title: str
    snippet: str
    publisher: str
    published_on: date | None
    last_updated: date | None
    kind: str
    rank: int

    def to_dict(self) -> dict:
        return {"idx": self.idx, "url": self.url, "title": self.title, "snippet": self.snippet,
                "publisher": self.publisher,
                "published_on": self.published_on.isoformat() if self.published_on else None,
                "last_updated": self.last_updated.isoformat() if self.last_updated else None,
                "kind": self.kind, "rank": self.rank}


@dataclass(frozen=True)
class EventDraft:
    title: str
    description: str
    category: str
    tags: tuple[str, ...]
    event_date: date
    date_basis: str  # searched_day | first_publication | extracted
    evidence: str  # contemporary | retrospective
    result_idx: tuple[int, ...]
    independent_sources: int
    flags: tuple[str, ...] = field(default_factory=tuple)
    extraction: str = "deterministic"  # deterministic | model

    def to_dict(self) -> dict:
        return {"title": self.title, "description": self.description, "category": self.category,
                "category_label": CATEGORIES.get(self.category, self.category), "tags": list(self.tags),
                "event_date": self.event_date.isoformat(), "date_basis": self.date_basis,
                "evidence": self.evidence, "result_idx": list(self.result_idx),
                "independent_sources": self.independent_sources, "flags": list(self.flags),
                "flag_messages": [FLAG_MESSAGES[f] for f in self.flags if f in FLAG_MESSAGES],
                "extraction": self.extraction}


# --- Parametri -------------------------------------------------------------------------------

def _clean_text(value, name: str, errors: list[str]) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        errors.append(f"'{name}' deve essere un testo")
        return None
    value = unicodedata.normalize("NFC", " ".join(value.split()))
    if len(value) > MAX_FILTER_LENGTH:
        errors.append(f"'{name}' supera {MAX_FILTER_LENGTH} caratteri")
    elif value and not _FILTER_TEXT.match(value):
        errors.append(f"'{name}' contiene caratteri non ammessi")
    return value or None


def _parse_day(value, name: str, errors: list[str]) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        errors.append(f"'{name}' deve essere una data YYYY-MM-DD")
        return None


def parse_search_params(data: dict, *, today: date) -> tuple[SearchParams | None, list[str]]:
    """Valida la richiesta: un giorno (`date`) oppure un intervallo breve (`start`, `end`)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return None, ["il corpo deve essere un oggetto JSON"]
    if data.get("date"):
        start = end = _parse_day(data["date"], "date", errors)
    else:
        start = _parse_day(data.get("start", ""), "start", errors)
        end = _parse_day(data.get("end") or data.get("start", ""), "end", errors)
    mode = data.get("mode") or "auto"
    if mode not in MODES:
        errors.append(f"'mode' deve essere uno tra: {', '.join(MODES)}")
    category = data.get("category") or None
    if category is not None and category not in CATEGORIES:
        errors.append("'category' non valida")
    topic = _clean_text(data.get("topic"), "topic", errors)
    region = _clean_text(data.get("region"), "region", errors)
    if start and end:
        if end < start:
            errors.append("la data finale precede quella iniziale")
        elif (end - start).days + 1 > MAX_RANGE_DAYS:
            errors.append(f"l'intervallo non può superare {MAX_RANGE_DAYS} giorni")
        if start < EARLIEST_DATE:
            errors.append(f"le date devono essere successive al {EARLIEST_DATE.isoformat()}")
        if end > today:
            errors.append("le date non possono essere future")
    if errors or start is None or end is None:
        return None, errors
    return SearchParams(start, end, mode, topic, region, category), []


# --- Query e richieste ----------------------------------------------------------------------

def _date_en(d: date) -> str:
    return f"{_MONTHS_EN[d.month - 1]} {d.day}, {d.year}"


def _date_it(d: date) -> str:
    return f"{d.day} {_MONTHS_IT[d.month - 1]} {d.year}"


def _period(params: SearchParams, fmt) -> str:
    if params.start == params.end:
        return fmt(params.start)
    return f"{fmt(params.start)} - {fmt(params.end)}"


def _subject(params: SearchParams) -> str:
    parts = [params.topic, CATEGORIES.get(params.category, "") if params.category else None, params.region]
    return " ".join(p for p in parts if p)


def build_requests(params: SearchParams) -> list[RequestSpec]:
    """Al massimo due richieste (una per tipo), ciascuna con al massimo quattro query."""
    subject = _subject(params)
    specs = []
    if params.mode in ("auto", "contemporary"):
        queries = ([f"{subject} news"] if subject else []) + [
            "top world news headlines", "stock markets news", "economy politics breaking news"]
        specs.append(RequestSpec("contemporary", tuple(queries[:MAX_QUERIES_PER_REQUEST]), params.start,
                                 params.end + timedelta(days=CONTEMPORARY_LAG_DAYS)))
    if params.mode in ("auto", "retrospective"):
        en, it = _period(params, _date_en), _period(params, _date_it)
        queries = ([f"{subject} {en}"] if subject else []) + [
            f"what happened on {en}", f"major news {en} markets", f"notizie {it}"]
        specs.append(RequestSpec("retrospective", tuple(queries[:MAX_QUERIES_PER_REQUEST]),
                                 params.start, None))
    return specs


# --- Risultati ------------------------------------------------------------------------------

def normalize_url(raw) -> str | None:
    """URL canonico http(s) senza frammenti né parametri di tracciamento; None se non valido."""
    if not isinstance(raw, str) or len(raw) > 2000:
        return None
    try:
        parsed = urlparse(raw.strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        return None
    host = parsed.hostname.lower().removeprefix("www.")
    if ":" in host:
        return None  # IPv6 letterale: non è una fonte giornalistica
    try:
        port = parsed.port
    except ValueError:
        return None  # porta non numerica o fuori intervallo
    if port and port not in (80, 443):
        host = f"{host}:{port}"
    query = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if not _TRACKING.match(k)])
    path = re.sub(r"/amp/?$", "", parsed.path).rstrip("/") or "/"
    return urlunparse(("https" if parsed.scheme == "https" else "http", host, path, "", query, ""))


def publisher_of(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def parse_provider_date(value) -> date | None:
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _plain(text) -> str:
    """Testo semplice: niente caratteri di controllo né markup; il frontend lo mostra come testo."""
    if not isinstance(text, str):
        return ""
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\t")
    return " ".join(re.sub(r"<[^>]{0,200}>", " ", text).split())


def accept_result(raw: dict, *, kind: str, rank: int, idx: int, params: SearchParams,
                  retrieved_on: date) -> tuple[NewsResult | None, str | None]:
    """Normalizza un risultato del provider. Restituisce (risultato, None) o (None, motivo)."""
    url = normalize_url(raw.get("url"))
    if url is None:
        return None, "invalid_url"
    title = _plain(raw.get("title"))[:MAX_TITLE]
    if not title:
        return None, "missing_title"
    if _latin_share(title) < MIN_LATIN_SHARE:
        return None, "other_language"
    if _INDEX_PAGE.search(title) or _is_date_only(title):
        return None, "index_page"
    published = parse_provider_date(raw.get("date"))
    if published and published > retrieved_on:
        published = None  # data nel futuro: non attendibile
    if kind == "contemporary":
        if published is None:
            return None, "missing_publication_date"
        window_end = params.end + timedelta(days=CONTEMPORARY_LAG_DAYS)
        if not params.start <= published <= window_end:
            return None, "outside_window"
    elif published is not None and published < params.start:
        return None, "published_before_event"
    return NewsResult(idx=idx, url=url, title=title, snippet=_plain(raw.get("snippet"))[:MAX_SNIPPET],
                      publisher=publisher_of(url), published_on=published,
                      last_updated=parse_provider_date(raw.get("last_updated")), kind=kind,
                      rank=rank), None


def _latin_share(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    latin = sum(1 for ch in letters if "LATIN" in unicodedata.name(ch, ""))
    return latin / len(letters)


def _is_date_only(title: str) -> bool:
    """Titoli come «24 Febbraio 2022»: pagine di archivio di un giorno, non articoli."""
    # Si ignora il nome della testata dopo « - » o « | ».
    head = re.split(r"\s[-|–]\s", title, maxsplit=1)[0]
    words = [t for t in _TOKEN.findall(head.lower()) if not t.isdigit()]
    return len([w for w in words if w not in _GENERIC and w not in _STOPWORDS]) == 0


def dedupe(results: list[NewsResult]) -> list[NewsResult]:
    """Stesso URL canonico → un solo risultato (si tiene il primo, cioè il meglio classificato)."""
    seen, unique = set(), []
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            unique.append(r)
    return unique


# --- Raggruppamento ----------------------------------------------------------------------------

def _tokens(text: str) -> frozenset[str]:
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return frozenset(t for t in _TOKEN.findall(plain) if len(t) > 2 and t not in _STOPWORDS)


def _similarity(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _salient(r: NewsResult) -> frozenset[str]:
    """Termini distintivi di titolo ed estratto: nomi e parole specifiche, non lessico di mercato."""
    return frozenset(t for t in _tokens(f"{r.title} {r.snippet[:300]}")
                     if t not in _GENERIC and not t.isdigit())


def _same_story(a_title, b_title, a_terms, b_terms) -> bool:
    if _similarity(a_title, b_title) >= CLUSTER_SIMILARITY:
        return True
    shared = a_terms & b_terms
    smaller = min(len(a_terms), len(b_terms))
    return len(shared) >= SHARED_TERMS_MIN and smaller > 0 and len(shared) / smaller >= SHARED_TERMS_OVERLAP


def cluster(results: list[NewsResult]) -> list[list[NewsResult]]:
    """Raggruppa i risultati che descrivono lo stesso fatto.

    Due risultati sono collegati se i titoli sono molto simili oppure se titolo ed estratto
    condividono abbastanza termini distintivi; i gruppi sono le componenti connesse. L'ordine
    segue il miglior rango del provider, mai i movimenti di mercato.
    """
    tokens = [_tokens(r.title) for r in results]
    terms = [_salient(r) for r in results]
    parent = list(range(len(results)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            if _same_story(tokens[i], tokens[j], terms[i], terms[j]):
                parent[find(j)] = find(i)
    groups: dict[int, list[NewsResult]] = {}
    for i, r in enumerate(results):
        groups.setdefault(find(i), []).append(r)
    return sorted(groups.values(), key=lambda g: min(r.rank for r in g))


def independent_sources(group: list[NewsResult]) -> tuple[int, bool]:
    """Editori distinti, contando una volta le copie con titolo identico (sindacazione)."""
    by_title: dict[str, set[str]] = {}
    for r in group:
        by_title.setdefault(" ".join(sorted(_tokens(r.title))), set()).add(r.publisher)
    syndicated = any(len(p) > 1 for p in by_title.values())
    seen_publishers: set[str] = set()
    count = 0
    for publishers in by_title.values():
        if publishers & seen_publishers:
            continue
        seen_publishers |= publishers
        count += 1
    return count, syndicated


def mentions_date(text: str, day: date) -> bool:
    lowered = text.lower()
    month_en, month_it = _MONTHS_EN[day.month - 1].lower(), _MONTHS_IT[day.month - 1]
    d = rf"(?<!\d)0?{day.day}(?!\d)"
    patterns = (
        rf"{month_en}\.? {d}(?:st|nd|rd|th)?\b",
        rf"{month_en[:3]}\.? {d}(?:st|nd|rd|th)?\b",
        rf"{d}(?:st|nd|rd|th)? (?:of )?{month_en}\b",
        rf"{d} {month_it}\b",
        rf"(?<!\d){day.isoformat()}(?!\d)",
    )
    return any(re.search(p, lowered) for p in patterns)


def guess_category(text: str, fallback: str | None, titles: str = "") -> tuple[str, bool]:
    """Categoria più citata nel gruppo: i titoli contano tre volte gli estratti; la categoria
    scelta dall'operatore come filtro, se presente, riceve un vantaggio."""
    body, heads = text.lower(), titles.lower()

    def hits(source: str, keyword: str) -> int:
        # Parole intere: «turmoil» non deve contare come «oil».
        return len(re.findall(_word(keyword), source))

    scores = {cat: sum(hits(body, k) + 2 * hits(heads, k) for k in words)
              for cat, words in _CATEGORY_KEYWORDS.items()}
    if fallback in scores:
        scores[fallback] += 2
    best = max(scores, key=scores.get)
    if scores[best] > (2 if fallback in scores else 0):
        return best, False
    return fallback or "political", fallback is None


def _word(keyword: str) -> str:
    """Espressione che trova la parola chiave solo come parola (o locuzione) intera."""
    return r"\b" + re.escape(keyword.strip()) + r"\b"


def guess_tags(text: str, category: str, region: str | None) -> tuple[str, ...]:
    lowered = text.lower()
    tags = [category.replace("_", "-")]
    for words in _CATEGORY_KEYWORDS.values():
        for word in words:
            if re.search(_word(word), lowered):
                slug = re.sub(r"[^a-z0-9]+", "-", word.strip().lower()).strip("-")
                if slug and slug not in tags:
                    tags.append(slug)
    if region:
        slug = re.sub(r"[^a-z0-9]+", "-",
                      unicodedata.normalize("NFKD", region.lower()).encode("ascii", "ignore").decode())
        if slug.strip("-"):
            tags.append(slug.strip("-"))
    return tuple(dict.fromkeys(tags))[:8]


def draft_event(group: list[NewsResult], params: SearchParams) -> EventDraft:
    """Scheda evento deterministica: testi e fonti provengono solo dai risultati del provider."""
    contemporary = [r for r in group if r.kind == "contemporary"]
    lead = min(contemporary or group, key=lambda r: r.rank)
    flags: list[str] = []
    text = " ".join(f"{r.title} {r.snippet}" for r in group)

    if params.start == params.end:
        event_date, basis = params.start, "searched_day"
    else:
        dates = [r.published_on for r in contemporary if r.published_on]
        in_range = [d for d in dates if params.start <= d <= params.end]
        event_date, basis = (min(in_range) if in_range else params.start), "first_publication"
        flags.append("date_estimated")
    # Ambiguità: in un intervallo, fonti dell'epoca pubblicate in giorni lontani tra loro possono
    # riferirsi a fatti diversi. Le ricostruzioni successive non contano: la loro data di
    # pubblicazione non dice nulla sul giorno dell'evento.
    contemporary_dates = [r.published_on for r in contemporary if r.published_on]
    if params.start != params.end and contemporary_dates and \
            (max(contemporary_dates) - min(contemporary_dates)).days > CONTEMPORARY_LAG_DAYS:
        flags.append("date_ambiguous")
    if not contemporary:
        flags.append("retrospective_only")
        if not any(mentions_date(f"{r.title} {r.snippet}", event_date) for r in group):
            flags.append("date_not_confirmed")
    if any(r.published_on is None for r in group):
        flags.append("missing_publication_date")
    count, syndicated = independent_sources(group)
    if count < 2:
        flags.append("single_source")
    if syndicated:
        flags.append("syndicated_copies")
    flags.append("snippet_only")
    category, defaulted = guess_category(text, params.category, " ".join(r.title for r in group))
    if defaulted:
        flags.append("category_default")
    return EventDraft(
        title=lead.title[:MAX_TITLE],
        description=(lead.snippet or lead.title)[:MAX_DESCRIPTION],
        category=category,
        tags=guess_tags(text, category, params.region),
        event_date=event_date,
        date_basis=basis,
        evidence="contemporary" if contemporary else "retrospective",
        result_idx=tuple(r.idx for r in sorted(group, key=lambda r: r.rank)),
        independent_sources=count,
        flags=tuple(dict.fromkeys(flags)),
    )


def rank_drafts(drafts: list[EventDraft]) -> list[EventDraft]:
    """Più fonti indipendenti prima; a parità, prima le fonti dell'epoca. Nessun dato di mercato."""
    return sorted(drafts, key=lambda d: (-d.independent_sources, d.evidence != "contemporary"))


def event_slug(title: str, day: date) -> str:
    base = unicodedata.normalize("NFKD", title.lower()).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:60].rstrip("-") or "evento"
    return f"{base}-{day.isoformat()}"
