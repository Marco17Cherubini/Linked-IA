"""Selezione dei precedenti storici.

Regole (versione metodo 2.0.0):
1. Candidati: eventi del catalogo diversi da quello analizzato.
2. Pertinenza: stessa categoria, oppure almeno `MIN_SHARED_TAGS` tag in comune.
3. Punteggio: 0,6 × stessa categoria + 0,4 × indice di Jaccard dei tag.
4. Cutoff: il precedente è utilizzabile solo se la sua seduta s=+MAX_HORIZON è
   anteriore o uguale alla seduta base dell'evento analizzato, nello stesso mercato.
   Così l'esito del precedente era osservabile al momento dell'evento.
5. Si tengono i primi `MAX_PRECEDENTS` per punteggio, a parità il più recente.
"""

from __future__ import annotations

from dataclasses import dataclass

from .events import Event

CATEGORY_WEIGHT = 0.6
TAGS_WEIGHT = 0.4
MIN_SHARED_TAGS = 2
MAX_PRECEDENTS = 6


@dataclass(frozen=True)
class Similarity:
    score: float
    same_category: bool
    shared_tags: tuple[str, ...]


def similarity(target: Event, candidate: Event) -> Similarity:
    a, b = set(target.tags), set(candidate.tags)
    shared = tuple(sorted(a & b))
    union = a | b
    jaccard = len(shared) / len(union) if union else 0.0
    same = target.category == candidate.category
    return Similarity(round(CATEGORY_WEIGHT * same + TAGS_WEIGHT * jaccard, 4), same, shared)


def is_relevant(sim: Similarity) -> bool:
    return sim.same_category or len(sim.shared_tags) >= MIN_SHARED_TAGS


def criteria() -> dict:
    return {
        "category_weight": CATEGORY_WEIGHT,
        "tags_weight": TAGS_WEIGHT,
        "min_shared_tags": MIN_SHARED_TAGS,
        "max_precedents": MAX_PRECEDENTS,
        "description": (
            "Precedenti della stessa categoria o con almeno "
            f"{MIN_SHARED_TAGS} tag in comune, ordinati per punteggio "
            f"({CATEGORY_WEIGHT} × categoria + {TAGS_WEIGHT} × Jaccard dei tag). "
            "Sono ammessi solo casi il cui esito era già osservabile alla seduta base."
        ),
    }
