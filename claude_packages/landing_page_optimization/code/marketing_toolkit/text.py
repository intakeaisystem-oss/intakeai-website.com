"""Text utilities: tokenizing, n-grams, TF-IDF cosine similarity, greedy
clustering, readability. Stdlib only, deterministic."""

from __future__ import annotations

import math
import re
from collections import Counter

STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have
having he her here hers herself him himself his how i if in into is it its itself just me more most
my myself no nor not now of off on once only or other our ours ourselves out over own same she should
so some such than that the their theirs them themselves then there these they this those through to
too under until up very was we were what when where which while who whom why will with would you your
yours yourself yourselves also get got really one even much still lot thing things im ive dont didnt
cant wont isnt doesnt wasnt ill youre theyre thats its it's i'm i've don't didn't can't won't isn't
doesn't wasn't i'll you're they're that's go going went make made use used using us well way see look looks honestly
""".split())

_WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def content_words(text: str) -> list[str]:
    return [w for w in words(text) if w not in STOPWORDS and len(w) > 2 and not w.isdigit()]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text) if len(s.strip()) > 2]


def ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def key_phrases(texts: list[str], top: int = 25, min_count: int = 2) -> list[tuple[str, int]]:
    """Frequent 1-3 word phrases (counted once per document) - the customer's own terms."""
    df: Counter = Counter()
    for t in texts:
        toks = content_words(t)
        grams = set(toks) | set(ngrams(toks, 2)) | set(ngrams(toks, 3))
        df.update(grams)
    items = [(g, c) for g, c in df.items() if c >= min_count]
    # prefer longer phrases when they are as frequent as their parts
    items.sort(key=lambda x: (-x[1], -len(x[0].split()), x[0]))
    out: list[tuple[str, int]] = []
    for g, c in items:
        gw = g.split()
        if any((g in o.split() or g in o) and oc >= c - 1 for o, oc in out):
            continue  # contained in an already-listed phrase
        if len(gw) > 1 and any(len(set(gw) & set(o.split())) >= 2 for o, _ in out):
            continue  # overlapping n-gram of a listed phrase
        if len(gw) == 1 and any(g in o.split() for o, _ in items[:top * 2] if len(o.split()) > 1 and _ >= c - 1):
            continue  # unigram mostly appears inside a longer phrase
        out.append((g, c))
        if len(out) >= top:
            break
    return out


def tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    docs = [Counter(content_words(t)) for t in texts]
    n = len(docs)
    df: Counter = Counter()
    for d in docs:
        df.update(d.keys())
    vecs = []
    for d in docs:
        v = {w: (c / max(1, sum(d.values()))) * (math.log((1 + n) / (1 + df[w])) + 1) for w, c in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def similarity(t1: str, t2: str) -> float:
    v = tfidf_vectors([t1, t2])
    return cosine(v[0], v[1])


def jaccard(t1: str, t2: str) -> float:
    a, b = set(content_words(t1)), set(content_words(t2))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster(texts: list[str], threshold: float = 0.35) -> list[list[int]]:
    """Greedy single-pass clustering on TF-IDF cosine against cluster centroids.
    Returns lists of indices, largest cluster first."""
    vecs = tfidf_vectors(texts)
    clusters: list[dict] = []
    for i, v in enumerate(vecs):
        best, best_sim = None, threshold
        for c in clusters:
            s = cosine(v, c["centroid"])
            if s >= best_sim:
                best, best_sim = c, s
        if best is None:
            clusters.append({"members": [i], "centroid": dict(v)})
        else:
            best["members"].append(i)
            k = len(best["members"])
            cen = best["centroid"]
            for w in set(cen) | set(v):
                cen[w] = (cen.get(w, 0.0) * (k - 1) + v.get(w, 0.0)) / k
    return sorted((c["members"] for c in clusters), key=len, reverse=True)


def syllables(word: str) -> int:
    w = word.lower().strip("'")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def readability(text: str) -> dict:
    """Flesch Reading Ease and Flesch-Kincaid grade (approximate, English)."""
    sents = max(1, len(sentences(text)))
    ws = words(text)
    if not ws:
        return {"flesch": None, "grade": None, "words": 0, "sentences": 0, "avg_sentence_words": 0}
    syl = sum(syllables(w) for w in ws)
    wps, spw = len(ws) / sents, syl / len(ws)
    return {
        "flesch": round(206.835 - 1.015 * wps - 84.6 * spw, 1),
        "grade": round(0.39 * wps + 11.8 * spw - 15.59, 1),
        "words": len(ws), "sentences": sents, "avg_sentence_words": round(wps, 1),
    }


def contains_any(text: str, phrases) -> list[str]:
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    hits = []
    for p in phrases:
        if re.search(r"(?<![a-z0-9])" + re.escape(p.lower()) + r"(?![a-z0-9])", low):
            hits.append(p)
    return hits
