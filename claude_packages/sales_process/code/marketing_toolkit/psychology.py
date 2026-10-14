"""Customer psychology and buying-behaviour engine.

build_profile() turns product info + customer language (+ optional behaviour
data) into a structured, evidence-tagged customer profile:

- Every insight has a `basis`: observed (customer said it, verbatim quote attached),
  measured (behavioural data supplied), inferred (reasoned from observed evidence)
  or hypothesis (plausible but untested), plus a confidence level and a way to validate it.
- 21 psychological dimensions are assessed separately; a dimension with no
  evidence is reported as "no evidence" + a validation method, never filled with
  generic assumptions. Customers are not assumed to share the same triggers.
"""

from __future__ import annotations

import re

from . import text as T
from . import voc as V

DIMENSIONS: dict[str, dict] = {
    "desires_outcomes": {"cues": ["want", "need", "goal", "wish", "hoping", "so that", "able to"],
                         "validate": "Interview: 'What would have to be true for this to be a success for you?'"},
    "problems_frustrations": {"cues": ["frustrat", "problem", "annoying", "struggle", "hassle", "pain", "waste"],
                              "validate": "Interview: 'Tell me about the last time this went wrong.'"},
    "emotional_motivation": {"cues": ["feel", "stress", "worr", "anxious", "peace of mind", "embarrass", "relief", "confident"],
                             "validate": "Interview follow-up: 'How did that make you feel?' and code answers."},
    "practical_motivation": {"cues": ["save time", "saves time", "cost", "faster", "efficient", "hours", "money", "revenue"],
                             "validate": "Survey: rank outcomes (time, money, quality, risk)."},
    "purchase_triggers": {"cues": ["finally", "decided", "last straw", "when we", "after we", "that's when", "started looking"],
                          "validate": "Switch interview: 'What happened that made you start looking?'"},
    "urgency_timing": {"cues": ["deadline", "asap", "urgent", "right now", "before", "season", "this week", "immediately"],
                       "validate": "Ask for timeline in discovery; compare time-to-purchase across segments."},
    "perceived_value": {"cues": ["worth", "value", "pays for itself", "roi", "for the price", "bang for"],
                        "validate": "Van Westendorp or willingness-to-pay interview questions."},
    "perceived_risk": {"cues": ["risk", "what if", "afraid", "lose", "mistake", "not sure", "gamble"],
                       "validate": "Ask 'What's the worst that could happen if you bought this?'"},
    "trust_credibility": {"cues": ["trust", "legit", "scam", "reliable", "reviews", "proof", "skeptic", "fake"],
                          "validate": "Test proof placement (A/B) and ask what would make them confident."},
    "social_proof": {"cues": ["recommended", "friend", "colleague", "everyone", "word of mouth", "reviews", "others"],
                     "validate": "Attribution survey: 'How did you hear about us?'"},
    "loss_aversion": {"cues": ["lose", "losing", "miss out", "missed", "penalty", "fine", "cost us", "wasted"],
                      "validate": "A/B test gain-framed vs loss-framed headline."},
    "cognitive_load": {"cues": ["confus", "complicated", "overwhelm", "too many", "hard to understand", "complex"],
                       "validate": "5-second test and task-completion usability test."},
    "decision_fatigue": {"cues": ["so many options", "compare", "couldn't decide", "research", "too many choices", "options"],
                         "validate": "Track pricing-page dwell and plan-choice abandonment."},
    "switching_costs": {"cues": ["migrat", "switch", "set up", "setup", "learning curve", "transfer", "contract", "import"],
                        "validate": "Ask current-solution users what stops them switching."},
    "status_identity": {"cues": ["professional", "reputation", "image", "impress", "look good", "proud", "credib"],
                        "validate": "Interview: 'Who else sees the result of this?'"},
    "convenience_effort": {"cues": ["easy", "simple", "quick", "effort", "hassle", "convenient", "one click"],
                           "validate": "Measure time-to-first-value and step completion."},
    "price_sensitivity": {"cues": ["expensive", "cheap", "price", "afford", "budget", "cost", "too much"],
                          "validate": "Price test on landing page (fake-door / plan anchoring) with approval."},
    "habits_alternatives": {"cues": ["spreadsheet", "excel", "paper", "used to", "currently", "always", "by hand", "manually"],
                            "validate": "Ask 'How do you handle this today?'"},
    "objections_friction": {"cues": ["but", "however", "concern", "hesita", "not ready", "contract", "commitment"],
                            "validate": "Log objections in sales calls; count by type."},
    "awareness_sophistication": {"cues": [], "validate": "Ask how they describe the problem and which solutions they tried."},
    "stated_vs_observed": {"cues": [], "validate": "Compare survey/interview statements with analytics or purchase data."},
}

URGENCY_NOW = ["deadline", "audit", "season", "inspection", "launch", "new hire", "growing", "fine", "penalty", "renewal"]
LATER_CUES = ["not now", "not ready", "next year", "later", "no time", "budget", "too expensive", "maybe"]


def _quotes_for(docs: list[dict], cues: list[str], limit: int = 2) -> tuple[int, list[dict]]:
    count, quotes = 0, []
    for d in docs:
        hit = False
        for s in T.sentences(d["text"]):
            low = s.lower()
            if any(c in low for c in cues):
                hit = True
                if len(quotes) < limit and d.get("quote_permitted", True):
                    quotes.append({"basis": "observed", "quote": s, "source_ref": d.get("source_ref", d.get("id", "?"))})
        count += hit
    return count, quotes


def _conf(n: int) -> str:
    return "high" if n >= 8 else "medium" if n >= 3 else "low"


def _theme_insights(result: dict | None, category: str, prefix: str, n: int = 5) -> list[dict]:
    out = []
    if not result:
        return out
    for i, th in enumerate(V.top_themes(result, category, n)):
        out.append({
            "id": f"{prefix}{i + 1}", "statement": th["label"], "statement_is_generated": True,
            "representative_quote": next((q["quote"] for q in th["quotes"] if q.get("verbatim")), None),
            "basis": "observed", "confidence": th["confidence"],
            "evidence": [{"basis": "observed", "quote": q["quote"], "source_ref": q["source_ref"]} for q in th["quotes"]],
            "document_count": th["document_count"],
            "validate_by": "Confirm with 3-5 more customers; check frequency in a larger sample.",
        })
    return out


def estimate_awareness(docs: list[dict], product_name: str | None, competitors: list[str]) -> dict:
    alltext = " ".join(d["text"].lower() for d in docs)
    prod = bool(product_name) and product_name.lower() in alltext
    comp = any(c.lower() in alltext for c in competitors)
    solution_words = any(w in alltext for w in ["software", "app", "tool", "service", "agency", "platform", "tried"])
    if prod:
        level = "product_aware"
    elif comp or solution_words:
        level = "solution_aware"
    elif docs:
        level = "problem_aware"
    else:
        level = "unknown"
    return {"level": level, "basis": "inferred" if docs else "hypothesis", "confidence": "low",
            "reason": ("mentions the product" if prod else "mentions competitors/solutions" if comp or solution_words
                       else "describes problems only" if docs else "no customer language supplied"),
            "note": "Awareness differs by segment and traffic source; treat as a starting hypothesis."}


def build_profile(product: dict, audience_description: str = "", documents: list[dict] | None = None,
                  voc_result: dict | None = None, competitors: list[str] | None = None,
                  stated_vs_observed: list[dict] | None = None) -> dict:
    """product: {"name", "category", "description", "price", "alternatives": [...]}.
    documents: VoC documents (see voc.analyze). stated_vs_observed: list of
    {"stated": "...", "observed": "...", "source": "..."} pairs supplied by the user."""
    documents = [dict(d, id=d.get("id", f"doc{i + 1}")) for i, d in enumerate(documents or [])]
    competitors = competitors or product.get("alternatives", []) or []
    if voc_result is None and documents:
        voc_result = V.analyze(documents, competitors=competitors)

    pains = _theme_insights(voc_result, "problem", "P") + _theme_insights(voc_result, "product_complaint", "PC", 3)
    outcomes = _theme_insights(voc_result, "desired_outcome", "O") + _theme_insights(voc_result, "valued_feature", "VF", 3)
    triggers = _theme_insights(voc_result, "purchase_trigger", "T")
    objections = _theme_insights(voc_result, "objection", "OB")
    distrust = [o for o in objections if re.search(r"trust|scam|skeptic|legit|fake|doubt|promise", " ".join(
        e["quote"].lower() for e in o["evidence"]))] + _theme_insights(voc_result, "unmet_expectation", "UE", 3)
    switching = _theme_insights(voc_result, "switching_reason", "SW", 3)

    # jobs to be done
    jtbd = []
    for o in outcomes[:3]:
        jtbd.append({"statement": f"Help me {o['statement']}", "statement_is_generated": True, "basis": "inferred",
                     "confidence": o["confidence"], "evidence": o["evidence"],
                     "validate_by": "Switch interviews: situation -> motivation -> outcome."})
    if not jtbd:
        desc = product.get("description") or product.get("name", "the product")
        jtbd.append({"statement": f"When [situation], I want to [job {desc} helps with], so I can [outcome]",
                     "statement_is_generated": True, "basis": "hypothesis", "confidence": "low", "evidence": [],
                     "validate_by": "Run 5-10 switch interviews before writing copy around this job."})

    if not triggers:
        triggers = [{"id": "T-h1", "statement": "Trigger unknown: no trigger language found in the inputs",
                     "basis": "hypothesis", "confidence": "low", "evidence": [],
                     "validate_by": DIMENSIONS["purchase_triggers"]["validate"]}]

    # buy now vs later
    now_n, now_q = _quotes_for(documents, URGENCY_NOW)
    later_n, later_q = _quotes_for(documents, LATER_CUES)
    buy_now = {"signals": now_q, "document_count": now_n, "basis": "observed" if now_n else "hypothesis",
               "note": "Real deadlines/events only. Never manufacture urgency."}
    buy_later = {"signals": later_q, "document_count": later_n, "basis": "observed" if later_n else "hypothesis"}

    alternatives = [{"name": a, "basis": "inferred", "note": "supplied by operator"} for a in product.get("alternatives", [])]
    for c in (voc_result or {}).get("competitor_mentions", []):
        alternatives.append({"name": c["competitor"], "basis": "observed", "document_count": c["document_count"],
                             "negative_context_count": c["negative_context_count"], "evidence": c["quotes"]})
    hab_n, hab_q = _quotes_for(documents, DIMENSIONS["habits_alternatives"]["cues"])
    if hab_n:
        alternatives.append({"name": "current workaround / DIY", "basis": "observed", "document_count": hab_n, "evidence": hab_q})

    # dimensions
    dims = {}
    for name, spec in DIMENSIONS.items():
        if name == "awareness_sophistication":
            dims[name] = estimate_awareness(documents, product.get("name"), competitors)
            continue
        if name == "stated_vs_observed":
            if stated_vs_observed:
                dims[name] = {"pairs": stated_vs_observed, "basis": "measured", "confidence": "medium",
                              "note": "Where they differ, trust observed behaviour for decisions; use stated language for copy."}
            else:
                dims[name] = {"pairs": [], "basis": "hypothesis", "confidence": "low",
                              "note": "No behavioural data supplied: all preferences here are stated, not observed.",
                              "validate_by": spec["validate"]}
            continue
        n, quotes = _quotes_for(documents, spec["cues"])
        if n:
            dims[name] = {"signal": "present", "document_count": n,
                          "share_of_documents": round(n / max(1, len(documents)), 2),
                          "basis": "observed", "confidence": _conf(n), "evidence": quotes, "validate_by": spec["validate"]}
        else:
            dims[name] = {"signal": "no evidence in inputs", "document_count": 0, "basis": "hypothesis",
                          "confidence": "low", "evidence": [], "validate_by": spec["validate"]}

    implications = messaging_implications(pains, outcomes, objections, distrust, dims, voc_result)
    hypotheses = [i for i in jtbd + triggers + pains + outcomes + objections if i.get("basis") == "hypothesis"]
    validation = [{"hypothesis": h["statement"], "method": h.get("validate_by", "")} for h in hypotheses]
    validation += [{"hypothesis": f"Dimension '{k}' matters for this audience", "method": v.get("validate_by", "")}
                   for k, v in dims.items() if v.get("basis") == "hypothesis"]

    segments_note = ("Single profile built from pooled inputs. If inputs mix segments (e.g. owners vs staff, "
                     "new vs returning), run build_profile per segment: triggers and objections usually differ.")
    return {
        "product": product.get("name"), "audience": audience_description,
        "inputs": {"documents": len(documents), "voc_used": bool(voc_result),
                   "behavioural_data": bool(stated_vs_observed)},
        "jobs_to_be_done": jtbd, "pain_points": pains, "desired_outcomes": outcomes,
        "purchase_triggers": triggers, "buy_now_vs_later": {"now": buy_now, "later": buy_later},
        "existing_alternatives": alternatives, "reasons_for_distrust": distrust, "objections": objections,
        "switching_reasons": switching, "dimensions": dims,
        "customer_terms": (voc_result or {}).get("customer_terms", [])[:15],
        "messaging_implications": implications, "validation_plan": validation,
        "segments_note": segments_note,
        "evidence_summary": {
            "observed_insights": sum(1 for i in pains + outcomes + objections + triggers if i.get("basis") == "observed"),
            "hypotheses": len(hypotheses),
            "dimensions_with_evidence": sum(1 for v in dims.values() if v.get("basis") == "observed"),
        },
    }


def _voice(ins: dict) -> str:
    q = ins.get("representative_quote")
    n = ins.get("document_count")
    return (f'"{q}"' if q else f"'{ins['statement']}' (keyword summary)") + (f" ({n} doc{'s' if n != 1 else ''})" if n else "")


def messaging_implications(pains, outcomes, objections, distrust, dims, voc_result) -> list[dict]:
    out = []
    terms = [t["phrase"] for t in (voc_result or {}).get("customer_terms", [])[:5]]
    if pains:
        out.append({"implication": f"Lead with the most frequent pain, in the customer's words: {_voice(pains[0])}",
                    "based_on": [pains[0]["id"]], "basis": "inferred",
                    "use_terms": terms})
    if outcomes:
        out.append({"implication": f"Frame the promise around the outcome customers ask for: {_voice(outcomes[0])}",
                    "based_on": [outcomes[0]["id"]], "basis": "inferred"})
    if objections:
        out.append({"implication": f"Answer the top objection before the CTA: {_voice(objections[0])}",
                    "based_on": [objections[0]["id"]], "basis": "inferred"})
    if distrust:
        out.append({"implication": "Place verifiable proof (named reviews, data, demo) next to every ask; avoid claims you cannot show",
                    "based_on": [d["id"] for d in distrust[:3]], "basis": "inferred"})
    if dims.get("cognitive_load", {}).get("basis") == "observed":
        out.append({"implication": "Reduce choices and jargon: one primary CTA, one plan highlighted, plain language",
                    "based_on": ["dimensions.cognitive_load"], "basis": "inferred"})
    if dims.get("price_sensitivity", {}).get("basis") == "observed":
        out.append({"implication": "Anchor price against the cost of the problem or current workaround; show what is included",
                    "based_on": ["dimensions.price_sensitivity"], "basis": "inferred"})
    if dims.get("switching_costs", {}).get("basis") == "observed":
        out.append({"implication": "Address switching effort explicitly (setup time, migration help, no lock-in if true)",
                    "based_on": ["dimensions.switching_costs"], "basis": "inferred"})
    if dims.get("loss_aversion", {}).get("basis") == "observed":
        out.append({"implication": "Test loss-framed messaging (what the current situation costs) against gain framing",
                    "based_on": ["dimensions.loss_aversion"], "basis": "hypothesis"})
    if not out:
        out.append({"implication": "Not enough customer evidence to derive messaging; collect VoC before writing copy",
                    "based_on": [], "basis": "hypothesis"})
    return out


def to_records(profile: dict, product: str | None = None, audience: str | None = None) -> list[dict]:
    recs = [{"kind": "customer_profile", "title": f"Customer profile: {profile.get('product') or product} / {audience or profile.get('audience') or 'all'}"[:300],
             "product": product or profile.get("product"), "audience": audience or profile.get("audience") or None,
             "confidence": "medium" if profile["evidence_summary"]["observed_insights"] >= 5 else "low",
             "basis": "inferred", "tags": ["profile"], "natural_key": f"profile|{product or profile.get('product')}|{audience or profile.get('audience')}",
             "data": profile}]
    for sec in ("pain_points", "desired_outcomes", "objections", "purchase_triggers"):
        for ins in profile[sec]:
            if ins.get("basis") == "hypothesis":
                continue
            recs.append({"kind": "customer_insight", "title": f"{sec}: {ins['statement']}"[:300],
                         "natural_key": f"insight|{product or profile.get('product')}|{audience or profile.get('audience') or ''}|{sec}|{ins['statement']}",
                         "product": product or profile.get("product"), "audience": audience or profile.get("audience") or None,
                         "confidence": ins["confidence"], "basis": ins["basis"], "tags": ["insight", sec],
                         "sources": sorted({e.get("source_ref", "") for e in ins.get("evidence", []) if e.get("source_ref")}),
                         "data": ins})
    return recs
