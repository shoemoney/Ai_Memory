"""Overlap checks between the v2 training data and an out-of-template test set."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pools as P  # noqa: E402

SLOT_VALUES = sorted(
    {v for name in dir(P) if isinstance(getattr(P, name), list) for v in map(str, getattr(P, name))}
    | {c[1] for c in P.CONCEPTS}
    | set(P.LANGS) | set(P.STYLES),
    key=len, reverse=True,
)


SLOT_RE = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(v) for v in SLOT_VALUES) + r")(?!\w)")


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower().replace("'", ""))


def frame_tokens(request: str) -> list[str]:
    """Request with every pooled slot value and every number replaced by one ARG token."""
    request = SLOT_RE.sub(" ARG ", request)
    request = re.sub(r"https?://\S+", " ARG ", request)
    request = re.sub(r"[\d][\d\s*+\-/().,]*", " ARG ", request)
    return [w for w in words(request) if w] if request.strip() else []


STOP = set("""a an the me my you your yours it its i im id ill ive we our us he she they them his her their
to of for on in at by with from into onto over out up as is are was were be been am do does did can could would
should will may might and or but nor so if then than that this these those there here what which who whom whose
when where why how not no yes any some one ones all each both more most other such only own same too very just
also give gave tell told get got show want need have has had make made let please thanks thank hey hi okay ok
about after before again through under between against during without within along across behind beyond arg""".split())


def grams(tokens: list[str], n: int = 3) -> set[tuple[str, ...]]:
    """Word n-grams that carry at least one content word (function words and light verbs alone
    do not make a phrase family)."""
    return {
        tuple(tokens[i : i + n])
        for i in range(len(tokens) - n + 1)
        if any(t not in STOP for t in tokens[i : i + n])
    }


def collapse(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        if t == "arg" and out and out[-1] == "arg":
            continue
        out.append(t)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / max(1, len(a | b))


def held_grams(text: str) -> set[tuple[str, ...]]:
    """Content n-grams of a held-out request, with and without slot replacement (the stricter union)."""
    text = re.sub(r"\{[a-z]\}", " ARG ", text)
    return grams(collapse(frame_tokens(text))) | grams(words(text))


class Blocker:
    """Rejects training requests that share a content 3-gram or a near-duplicate with a held-out set."""

    def __init__(self, heldout: list[str]):
        self.grams: set[tuple[str, ...]] = set().union(*(held_grams(t) for t in heldout))
        self.sets = [set(words(t)) for t in heldout]

    def blocked(self, request: str) -> bool:
        if grams(collapse(frame_tokens(request))) & self.grams:
            return True
        w = set(words(request))
        return any(jaccard(w, h) >= 0.6 for h in self.sets)


def report(train_requests: list[str], heldout: list[str], frames: list[str] | None = None) -> dict:
    """Frame 3-gram overlap (frames: held-out templates with slots as {x}, else the requests) and
    near-duplicate requests. Empty lists mean zero overlap."""
    train_grams: set[tuple[str, ...]] = set().union(
        *(grams(collapse(frame_tokens(r))) for r in train_requests)
    )
    gram_hits = []
    for text in frames if frames is not None else heldout:
        shared = held_grams(text) & train_grams
        if shared:
            gram_hits.append((text, sorted(shared)[:3]))
    train_sets = [set(words(r)) for r in train_requests]
    near = []
    for text in heldout:
        h = set(words(text))
        best = max((jaccard(h, t) for t in train_sets), default=0.0)
        if best >= 0.6 or text in set(train_requests):
            near.append((text, round(best, 2)))
    return {"frame_3gram_hits": gram_hits, "near_duplicates": near}
