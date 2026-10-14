"""Voice-of-customer analyzer.

Input: documents (reviews, interviews, tickets, surveys, churn reasons ...),
each {"id", "text", "source_type", "source_ref", "rating", "quote_permitted"}.

Output: categorized themes with frequencies, document counts, confidence,
verbatim representative quotes with source references, the customer's own
terminology, emotional language and competitor mentions.

Separation of real vs generated language:
- `quotes[*].quote` is always an exact substring of an input document (verbatim=True).
- `themes[*].label` is a machine-generated keyword summary and is marked as such.
Classification is rule-based (cue phrases), so it is transparent and
deterministic but imperfect: treat categories as a first pass for human review.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from . import text as T
from .schemas import VOC_DOCUMENT, validate

CATEGORY_CUES: dict[str, list[str]] = {
    "problem": [
        r"\bproblem\b", r"\bissue\b", r"\bstruggl", r"\bhard to\b", r"\bdifficult", r"\bpain\b", r"\bwast(e|ed|ing)\b",
        r"\btakes? (forever|too long|hours)", r"\bkeeps? (crashing|breaking|failing)", r"\bconfus", r"\bfrustrat",
        r"\bhassle", r"\btedious", r"\bmanual(ly)?\b", r"\bcan'?t (figure|find|get)", r"\bnightmare\b", r"\bheadache",
    ],
    "desired_outcome": [
        r"\bi (just )?want(ed)?\b", r"\bi need(ed)?\b", r"\bwish\b", r"\bhoping\b", r"\bwould love\b", r"\bgoal\b",
        r"\bso that\b", r"\bable to\b", r"\blooking for\b", r"\bif only\b", r"\bwhat i (really )?need",
    ],
    "objection": [
        r"\btoo expensive\b", r"\bexpensive\b", r"\bprice(y| is too)", r"\bnot worth\b", r"\bnot sure\b", r"\bworried\b",
        r"\bconcern", r"\bskeptic", r"\bdon'?t trust\b", r"\bhesita", r"\bscam\b", r"\bcontract\b", r"\bcommitment\b",
        r"\bno time\b", r"\bnot (ready|now)\b", r"\bdoubt", r"\bwhat if\b", r"\bafraid\b",
    ],
    "switching_reason": [
        r"\bswitch(ed|ing)? (from|to)\b", r"\bmoved (from|to|over)\b", r"\bused to use\b", r"\breplaced\b",
        r"\bmigrat", r"\bleft (for|because)\b", r"\bcompared to\b", r"\binstead of\b",
    ],
    "purchase_trigger": [
        r"\bfinally\b", r"\bthe last straw\b", r"\bafter (we|i) (lost|missed|got|had)", r"\bwhen (we|i) (started|grew|hired)",
        r"\bdecided to\b", r"\bthat'?s when\b", r"\bdeadline\b", r"\baudit\b", r"\bnew (job|role|season|year)\b",
        r"\bwas recommended\b", r"\bsaw an ad\b", r"\ba friend\b",
    ],
    "product_complaint": [
        r"\bbug(s|gy)?\b", r"\bcrash", r"\bslow\b", r"\bbroken\b", r"\bdoesn'?t work\b", r"\bglitch", r"\berror",
        r"\bclunky\b", r"\bpoor (support|service|quality)", r"\bterrible\b", r"\bawful\b", r"\bdisappoint", r"\bunreliable",
    ],
    "unmet_expectation": [
        r"\bexpected\b", r"\bpromised\b", r"\badvertised\b", r"\bthought it would\b", r"\bnot as described\b",
        r"\bmisleading\b", r"\bsupposed to\b", r"\bclaimed\b", r"\bfell short\b",
    ],
    "valued_feature": [
        r"\blove\b", r"\bfavorite\b", r"\bfavourite\b", r"\bbest (part|thing|feature)", r"\bgreat\b", r"\bsaves? (me|us)\b",
        r"\beasy to\b", r"\bhelpful\b", r"\bgame.?changer\b", r"\bcan'?t live without\b", r"\bexcellent\b", r"\bworks (great|well)",
    ],
    "abandonment_reason": [
        r"\bcancel", r"\bunsubscrib", r"\bstopped using\b", r"\bgave up\b", r"\buninstall", r"\bdeleted\b",
        r"\bchurn", r"\bwon'?t renew\b", r"\bnot renewing\b", r"\bquit\b", r"\brefund\b",
    ],
}

EMOTION_WORDS = [
    "frustrated", "frustrating", "annoyed", "annoying", "angry", "furious", "hate", "stressed", "stressful",
    "anxious", "worried", "afraid", "scared", "overwhelmed", "embarrassed", "exhausted", "tired", "fed up",
    "disappointed", "confused", "relieved", "love", "happy", "delighted", "thrilled", "grateful", "excited",
    "confident", "peace of mind", "nightmare", "lifesaver", "painful", "hopeless", "desperate",
]


def _classify(sentence: str) -> list[str]:
    low = sentence.lower()
    return [cat for cat, cues in CATEGORY_CUES.items() if any(re.search(c, low) for c in cues)]


def _label_terms(sents: list[str], n: int = 3) -> list[str]:
    """Bigrams shared by >=2 sentences, then the most frequent content words."""
    bi: Counter = Counter()
    uni: Counter = Counter()
    for s in sents:
        toks = T.content_words(s)
        bi.update(set(T.ngrams(toks, 2)))
        uni.update(set(toks))
    out: list[str] = []
    for b, c in sorted(bi.items(), key=lambda x: (-x[1], x[0])):
        if c >= 2 and len(out) < n and not set(b.split()) & {w for o in out for w in o.split()}:
            out.append(b)
    for w, _ in sorted(uni.items(), key=lambda x: (-x[1], x[0])):
        if len(out) >= n:
            break
        if not any(w in o.split() for o in out):
            out.append(w)
    return out


def _dedupe(docs: list[dict], threshold: float) -> tuple[list[dict], list[str]]:
    kept, removed = [], []
    vecs = T.tfidf_vectors([d["text"] for d in docs])
    kept_idx: list[int] = []
    for i, d in enumerate(docs):
        norm = " ".join(d["text"].lower().split())
        dup = False
        for j in kept_idx:
            if norm == " ".join(docs[j]["text"].lower().split()) or T.cosine(vecs[i], vecs[j]) >= threshold:
                dup = True
                break
        if dup:
            removed.append(d["id"])
        else:
            kept_idx.append(i)
            kept.append(d)
    return kept, removed


def _confidence(doc_count: int, source_types: int, total_docs: int) -> str:
    if doc_count >= 10 or (doc_count >= 5 and source_types >= 2):
        return "high"
    if doc_count >= 3:
        return "medium"
    return "low"


def analyze(documents: list[dict], competitors: list[str] | None = None,
            cluster_threshold: float = 0.35, near_duplicate_threshold: float = 0.85,
            max_quotes: int = 3) -> dict:
    if not documents:
        raise ValueError("no documents supplied")
    docs = []
    for i, d in enumerate(documents):
        d = dict(d)
        d.setdefault("id", f"doc{i + 1}")
        d.setdefault("source_type", "other")
        d.setdefault("source_ref", d["id"])
        validate(d, VOC_DOCUMENT)
        docs.append(d)
    docs, removed = _dedupe(docs, near_duplicate_threshold)

    # sentence-level classification
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        for s in T.sentences(d["text"]):
            for cat in _classify(s):
                by_cat[cat].append({"sentence": s, "doc": d})

    categories = {}
    for cat in CATEGORY_CUES:
        items = by_cat.get(cat, [])
        if not items:
            categories[cat] = {"mention_count": 0, "document_count": 0, "share_of_documents": 0.0,
                               "confidence": "none", "themes": []}
            continue
        groups = T.cluster([it["sentence"] for it in items], cluster_threshold)
        themes = []
        for g in groups:
            members = [items[i] for i in g]
            doc_ids = {m["doc"]["id"] for m in members}
            stypes = {m["doc"]["source_type"] for m in members}
            terms = _label_terms([m["sentence"] for m in members])
            quotes, seen = [], set()
            for m in sorted(members, key=lambda m: len(m["sentence"])):
                if m["doc"]["id"] in seen or len(m["sentence"]) < 12:
                    continue
                seen.add(m["doc"]["id"])
                permitted = m["doc"].get("quote_permitted", True)
                quotes.append({
                    "quote": m["sentence"] if permitted else "[quote withheld: not permitted]",
                    "verbatim": bool(permitted), "doc_id": m["doc"]["id"],
                    "source_type": m["doc"]["source_type"], "source_ref": m["doc"]["source_ref"]})
                if len(quotes) >= max_quotes:
                    break
            themes.append({
                "label": " / ".join(terms[:3]) or members[0]["sentence"][:40],
                "label_is_generated": True,
                "mention_count": len(members), "document_count": len(doc_ids),
                "source_types": sorted(stypes),
                "confidence": _confidence(len(doc_ids), len(stypes), len(docs)),
                "quotes": quotes,
            })
        cat_docs = {it["doc"]["id"] for it in items}
        categories[cat] = {
            "mention_count": len(items), "document_count": len(cat_docs),
            "share_of_documents": round(len(cat_docs) / len(docs), 3),
            "confidence": _confidence(len(cat_docs), len({it["doc"]["source_type"] for it in items}), len(docs)),
            "themes": themes,
        }

    # emotional language
    emo: Counter = Counter()
    for d in docs:
        for w in T.contains_any(d["text"], EMOTION_WORDS):
            emo[w] += 1
    # competitor mentions
    comp_out = []
    for name in competitors or []:
        hits = [d for d in docs if re.search(r"\b" + re.escape(name.lower()) + r"\b", d["text"].lower())]
        if hits:
            neg = sum(1 for d in hits if _classify(d["text"]) and set(_classify(d["text"])) &
                      {"product_complaint", "abandonment_reason", "unmet_expectation", "switching_reason"})
            comp_out.append({
                "competitor": name, "document_count": len(hits), "negative_context_count": neg,
                "quotes": [{"quote": s, "verbatim": True, "doc_id": d["id"], "source_ref": d["source_ref"]}
                           for d in hits[:max_quotes] for s in T.sentences(d["text"]) if name.lower() in s.lower()][:max_quotes],
            })

    ratings = [d["rating"] for d in docs if isinstance(d.get("rating"), (int, float))]
    limitations = ["Classification uses cue phrases: review the themes before relying on them."]
    if len(docs) < 20:
        limitations.append(f"Only {len(docs)} unique documents: frequencies are indicative, not representative.")
    if len({d['source_type'] for d in docs}) == 1:
        limitations.append("Single source type: findings may reflect that channel's bias (e.g. reviews skew extreme).")
    if ratings and (sum(1 for r in ratings if r <= 2) + sum(1 for r in ratings if r >= 4)) / len(ratings) > 0.9:
        limitations.append("Ratings are polarised: typical of review sites, middle opinions are under-represented.")

    return {
        "documents_received": len(documents), "documents_used": len(docs),
        "near_duplicates_removed": removed,
        "sources_by_type": dict(Counter(d["source_type"] for d in docs)),
        "categories": categories,
        "customer_terms": [{"phrase": p, "document_count": c} for p, c in T.key_phrases([d["text"] for d in docs], top=30)],
        "emotional_language": [{"term": t, "document_count": c} for t, c in emo.most_common()],
        "competitor_mentions": comp_out,
        "rating_summary": ({"n": len(ratings), "mean": round(sum(ratings) / len(ratings), 2),
                            "low_1_2": sum(1 for r in ratings if r <= 2), "high_4_5": sum(1 for r in ratings if r >= 4)}
                           if ratings else None),
        "limitations": limitations,
        "provenance_note": "Quotes are verbatim substrings of the input. Theme labels are generated keyword summaries.",
    }


def top_themes(result: dict, category: str, n: int = 5) -> list[dict]:
    return sorted(result["categories"].get(category, {}).get("themes", []),
                  key=lambda t: (-t["document_count"], -t["mention_count"]))[:n]


def to_records(result: dict, product: str | None = None, audience: str | None = None) -> list[dict]:
    """Convert themes into store records (kind=voc_finding)."""
    recs = []
    for cat, info in result["categories"].items():
        for th in info["themes"]:
            if th["document_count"] < 2 and th["confidence"] == "low":
                continue
            recs.append({
                "kind": "voc_finding", "title": f"{cat}: {th['label']}"[:300],
                "product": product, "audience": audience, "confidence": th["confidence"], "basis": "observed",
                "tags": ["voc", cat], "sources": sorted({q["source_ref"] for q in th["quotes"]}),
                "natural_key": f"{product or ''}|{cat}|{th['label']}",
                "data": {"category": cat, **th},
            })
    return recs
