"""Sales conversation and objection-handling engine.

- OBJECTIONS: structured library (expressed objection, underlying reasons,
  clarifying questions, evidence to offer, truthful response pattern, when to
  walk away, when the offer is genuinely unsuitable, what to improve).
- classify_objection() / handle_objection(): map a buyer's words to the library
  and build a handling plan that may legitimately end in "disqualify" or
  "improve the offer". Overcoming objections "at any cost" is not a goal.
- qualify(): configurable lead qualification with disqualifiers.
- STAGES + discovery_questions(): frameworks for the full sales cycle across
  B2B services, software, consumer apps, e-commerce and high-consideration sales.
- ObjectionLog: persist real objections and outcomes to learn frequencies.
"""

from __future__ import annotations

import re
from collections import Counter

from .store import KnowledgeStore

OBJECTIONS: dict[str, dict] = {
    "price": {
        "patterns": [r"too expensive", r"too much", r"pricey", r"cheaper", r"can'?t justify", r"cost(s)? (a lot|too)", r"price is high"],
        "underlying": ["Value not yet clear relative to price", "Comparing against a cheaper but different alternative",
                       "Genuinely no budget", "Negotiation tactic", "Risk feels high for the amount"],
        "clarify": ["Compared to what?", "If price weren't a factor, would this be the right solution?",
                    "What does the problem cost you today (time, money, risk)?", "Is it the total, or how it's paid?"],
        "evidence": ["cost-of-problem calculation using their numbers", "verified case with comparable customer", "itemised inclusions"],
        "response": "Acknowledge; clarify the comparison; connect price to the cost of the problem using THEIR numbers; offer a smaller scope if it truly fits.",
        "walk_away": ["Their realistic value from solving the problem is below your price", "They only buy on lowest price"],
        "unsuitable_when": "The buyer's problem is small enough that a cheaper alternative serves them well.",
        "improve_offer_if": "Many qualified buyers say this: test packaging, entry offer or payment terms.",
    },
    "no_budget": {
        "patterns": [r"no budget", r"don'?t have the (money|budget)", r"can'?t afford", r"budget (is )?(frozen|spent|cut)"],
        "underlying": ["Budget cycle timing", "Not a priority vs other spend", "Real cash constraint"],
        "clarify": ["When is budget set?", "Who controls it?", "Is this a 'not now' or a 'not ever'?"],
        "evidence": ["ROI/payback estimate with their inputs (labelled estimate)"],
        "response": "Respect it; find out when budget opens and who decides; offer to stay in touch with useful info.",
        "walk_away": ["No budget path within a reasonable horizon"],
        "unsuitable_when": "They cannot afford it without harming their business/finances.",
        "improve_offer_if": "Frequent among ideal customers: consider lower-cost tier.",
    },
    "timing": {
        "patterns": [r"not (right )?now", r"bad time", r"next (quarter|year|month)", r"maybe later", r"too busy", r"no time", r"after (the|our)"],
        "underlying": ["Low urgency", "Implementation effort feared", "Competing priorities", "Polite brush-off"],
        "clarify": ["What would need to change for this to be a priority?", "What happens if this waits 6 months?", "Is it the timing or the effort?"],
        "evidence": ["implementation timeline and effort required from them"],
        "response": "Quantify cost of delay with their input (honestly); if timing is real, agree a specific follow-up date.",
        "walk_away": ["No consequence to waiting and no trigger expected"],
        "unsuitable_when": "Their problem genuinely isn't pressing.",
        "improve_offer_if": "Effort is the real blocker: offer done-for-you onboarding.",
    },
    "need_unclear": {
        "patterns": [r"don'?t (really )?need", r"we'?re (fine|ok|good)", r"not (a|really a) problem", r"doing (fine|ok) without"],
        "underlying": ["Problem not recognised", "Wrong person/segment", "Already solved"],
        "clarify": ["How do you handle X today?", "What would you improve about it?", "How much time does it take?"],
        "evidence": ["benchmarks or examples from similar customers (verified)"],
        "response": "Explore their current process; if there's genuinely no problem, thank them and leave.",
        "walk_away": ["No meaningful problem after discovery"],
        "unsuitable_when": "They don't have the problem the product solves.",
        "improve_offer_if": "Many target prospects say this: revisit targeting/ICP.",
    },
    "trust": {
        "patterns": [r"never heard of", r"how do i know", r"scam", r"sounds too good", r"skeptic", r"prove it", r"is this legit", r"don'?t trust"],
        "underlying": ["New/unknown brand", "Past bad experience", "Claims sounded exaggerated"],
        "clarify": ["What would you need to see to feel confident?", "Have you been burned by something similar?"],
        "evidence": ["verifiable reviews", "references they can call", "demo with their data", "pilot", "clear refund terms (if real)"],
        "response": "Don't argue: offer verifiable proof and a low-risk way to test; tone down any claims you can't show.",
        "walk_away": ["They require proof you don't have yet: offer a pilot or come back later"],
        "unsuitable_when": "You lack the credentials they legitimately need (e.g. compliance certification).",
        "improve_offer_if": "Recurring: invest in case studies, reviews, guarantees you can honour.",
    },
    "authority": {
        "patterns": [r"(talk|check) (to|with) my (boss|partner|wife|husband|team|manager)", r"not my decision", r"need approval", r"run it by"],
        "underlying": ["Not the decision maker", "Wants cover for the decision", "Unconvinced and deflecting"],
        "clarify": ["Who else is involved and what matters to them?", "What will you recommend?", "Can we include them in the next call?"],
        "evidence": ["one-page summary for the decision maker", "ROI estimate"],
        "response": "Equip your champion: summary, answers to the decision maker's likely concerns, offer a joint call.",
        "walk_away": ["No access to decision maker and champion not convinced"],
        "unsuitable_when": "",
        "improve_offer_if": "",
    },
    "competitor": {
        "patterns": [r"(already|currently) (use|using|have)", r"looking at (other|another)", r"\bvs\b", r"compared to", r"(competitor|alternative)"],
        "underlying": ["Comparing options", "Satisfied with incumbent", "Using you for price leverage"],
        "clarify": ["What do you like about it?", "What would you change?", "What made you take this call?"],
        "evidence": ["fair, verifiable comparison", "switching support details"],
        "response": "Be fair about the competitor; focus on the specific gap they mentioned; never disparage or make unverifiable comparisons.",
        "walk_away": ["Incumbent fits them better"],
        "unsuitable_when": "The competitor genuinely serves their needs better: say so.",
        "improve_offer_if": "Lost repeatedly on the same gap: product or positioning work.",
    },
    "status_quo": {
        "patterns": [r"spreadsheet", r"do it (ourselves|myself|in-house|manually)", r"by hand", r"our own (system|way)"],
        "underlying": ["Switching seems riskier than the pain", "Hidden cost of DIY not visible"],
        "clarify": ["How much time does that take per week?", "What breaks when someone is away?"],
        "evidence": ["time/cost comparison using their numbers"],
        "response": "Make the cost of the current workaround visible, honestly; reduce switching risk.",
        "walk_away": ["DIY genuinely costs them less"],
        "unsuitable_when": "Their volume is too small to justify a tool/service.",
        "improve_offer_if": "",
    },
    "switching_cost": {
        "patterns": [r"migrat", r"switch(ing)? (is|would be)", r"set ?up (time|effort)", r"learning curve", r"retrain", r"data (transfer|import)"],
        "underlying": ["Fear of disruption", "Sunk cost in current tool", "Time to implement"],
        "clarify": ["What part of switching worries you most?", "What would a smooth transition look like?"],
        "evidence": ["migration plan", "onboarding timeline", "support commitments"],
        "response": "Lay out the real migration steps, time and help provided.",
        "walk_away": [],
        "unsuitable_when": "The disruption outweighs the benefit for them right now.",
        "improve_offer_if": "Offer migration/onboarding service.",
    },
    "complexity": {
        "patterns": [r"complicated", r"too complex", r"hard to use", r"confusing", r"overwhelming", r"not (very )?tech"],
        "underlying": ["Bad demo", "Low tech confidence", "Product genuinely complex"],
        "clarify": ["Which part felt complicated?", "Who would use it day to day?"],
        "evidence": ["short task demo", "onboarding support"],
        "response": "Show the 2-3 tasks they actually need, not every feature; offer onboarding help.",
        "walk_away": [],
        "unsuitable_when": "The product truly requires skills they don't have and won't acquire.",
        "improve_offer_if": "Product UX / onboarding improvement.",
    },
    "send_info": {
        "patterns": [r"send (me )?(some )?(info|information|details|a brochure|an email)", r"email me", r"i'?ll (think|get back)"],
        "underlying": ["Polite exit", "Genuine need to review", "Not convinced"],
        "clarify": ["Happy to. What specifically would be most useful?", "What would you look for in it to decide?"],
        "evidence": ["tailored one-pager answering their specific question"],
        "response": "Agree, ask what matters, send something specific, and book a follow-up time.",
        "walk_away": ["No reply after a reasonable follow-up sequence"],
        "unsuitable_when": "",
        "improve_offer_if": "",
    },
    "commitment": {
        "patterns": [r"contract", r"lock(ed)? in", r"long[- ]term", r"commitment", r"cancel(lation)? (policy|terms)"],
        "underlying": ["Fear of being stuck with a bad decision"],
        "clarify": ["What term would feel comfortable?", "What would make you confident in a longer term?"],
        "evidence": ["exact cancellation terms", "pilot option"],
        "response": "State terms plainly; offer a shorter term or pilot if commercially viable.",
        "walk_away": [],
        "unsuitable_when": "",
        "improve_offer_if": "Common objection: test monthly or pilot terms.",
    },
    "results_doubt": {
        "patterns": [r"will (it|this) (really )?work", r"doesn'?t work for", r"our (industry|case) is different", r"tried (that|this|something) before"],
        "underlying": ["Past failure", "Unique situation", "Claims sounded generic"],
        "clarify": ["What happened last time?", "What's different about your situation?"],
        "evidence": ["comparable verified case", "pilot with agreed success criteria"],
        "response": "Explain honestly when it works and when it doesn't; propose a measurable pilot.",
        "walk_away": ["Their situation matches known failure cases"],
        "unsuitable_when": "Evidence suggests it won't work for their case.",
        "improve_offer_if": "",
    },
    "security_compliance": {
        "patterns": [r"security", r"gdpr", r"hipaa", r"soc ?2", r"compliance", r"data (privacy|protection)", r"legal (team|review)"],
        "underlying": ["Regulatory requirement", "Procurement checklist"],
        "clarify": ["Which requirements specifically?", "Who reviews this on your side?"],
        "evidence": ["actual certifications/policies (only those you hold)", "DPA", "security documentation"],
        "response": "Answer precisely with documents you actually have; never claim certifications you don't hold.",
        "walk_away": ["They require certifications you don't have"],
        "unsuitable_when": "You can't meet a mandatory requirement.",
        "improve_offer_if": "Frequent in target segment: roadmap compliance work.",
    },
    "feature_gap": {
        "patterns": [r"does (it|this) (have|do|support)", r"missing", r"doesn'?t (have|support|integrate)", r"need (it )?to integrate"],
        "underlying": ["Must-have requirement", "Nice-to-have used as objection"],
        "clarify": ["How do you use that today?", "Is this a must-have for day one?"],
        "evidence": ["honest roadmap status", "workaround (if real)"],
        "response": "Say clearly whether it exists; don't promise roadmap dates you can't keep.",
        "walk_away": ["Must-have feature missing"],
        "unsuitable_when": "A required capability is missing.",
        "improve_offer_if": "Many prospects need it: product priority signal.",
    },
}

STAGES: dict[str, dict] = {
    "qualification": {"goal": "Decide quickly whether to invest time", "exit": "Problem, budget path, authority and timing known or plan to learn them",
                      "mistakes": ["Pitching before qualifying", "Treating every lead as a fit"]},
    "discovery": {"goal": "Understand situation, problem, impact and desired outcome in their words",
                  "exit": "Buyer has articulated the problem's cost and what success looks like", "mistakes": ["Talking more than listening", "Leading questions"]},
    "needs_analysis": {"goal": "Map requirements to capabilities honestly", "exit": "Must-haves vs nice-to-haves agreed", "mistakes": ["Ignoring gaps"]},
    "demonstration": {"goal": "Show the 2-3 workflows that solve their stated problem", "exit": "Buyer can picture using it",
                      "mistakes": ["Feature tours", "Demoing things they didn't ask for"]},
    "follow_up": {"goal": "Keep momentum with useful, specific contact", "exit": "Next step booked or clear no",
                  "mistakes": ["'Just checking in' emails", "No agreed next step"]},
    "pricing_discussion": {"goal": "Present price anchored to value and scope", "exit": "Price understood; concerns surfaced",
                           "mistakes": ["Apologising for price", "Discounting before understanding the objection"]},
    "objection_handling": {"goal": "Understand the real concern and respond truthfully", "exit": "Concern resolved, offer adjusted, or disqualified",
                           "mistakes": ["Arguing", "Scripted rebuttals", "Overcoming at any cost"]},
    "negotiation": {"goal": "Trade value for value", "exit": "Terms both sides can live with",
                    "mistakes": ["Unilateral concessions", "Agreeing to terms you can't fulfil"]},
    "closing": {"goal": "Ask clearly for the decision", "exit": "Signed / paid, or a clear no with reason logged", "mistakes": ["Pressure tactics", "Fake deadlines"]},
    "retention": {"goal": "Deliver the promised outcome and confirm it", "exit": "Customer reaches value; renewal risk known",
                  "mistakes": ["Disappearing after the sale"]},
    "upsell_cross_sell": {"goal": "Offer more only where it serves the customer", "exit": "Expansion tied to their goals",
                          "mistakes": ["Upselling before initial value is delivered"]},
}

DISCOVERY: dict[str, dict[str, list[str]]] = {
    "_common": {
        "situation": ["How do you handle this today?", "Who's involved?"],
        "problem": ["What's frustrating about the current way?", "When did it last go wrong?"],
        "impact": ["What does that cost you in time or money?", "What happens if nothing changes?"],
        "outcome": ["What would success look like in 90 days?", "How would you measure it?"],
        "decision": ["How do you usually decide on something like this?", "Who else needs to be comfortable with it?"],
        "alternatives": ["What else are you considering, including doing nothing?"],
    },
    "b2b_services": {"impact": ["How much revenue is affected?"], "decision": ["What's your procurement process?"]},
    "software": {"situation": ["What tools does this need to work with?"], "decision": ["Who will administer it?"]},
    "consumer_app": {"situation": ["When during your day would you use this?"], "problem": ["What have you tried already?"]},
    "ecommerce": {"problem": ["What stopped you from buying last time?"], "outcome": ["What would make this an easy yes?"]},
    "high_consideration": {"decision": ["What's your timeline and what drives it?", "What would make you regret this decision?"]},
}

DEFAULT_QUAL = {
    "problem": {"weight": 2, "question": "Do they have the problem, and how painful is it?"},
    "budget": {"weight": 1.5, "question": "Is there a realistic budget path?"},
    "authority": {"weight": 1, "question": "Are we talking to (or can we reach) the decision maker?"},
    "timing": {"weight": 1, "question": "Is there a reason to act in the next 90 days?"},
    "fit": {"weight": 2, "question": "Does our offer actually solve their version of the problem?"},
    "engagement": {"weight": 0.5, "question": "Are they responsive and sharing information?"},
}


def classify_objection(text: str) -> list[dict]:
    low = text.lower()
    out = []
    for k, o in OBJECTIONS.items():
        hits = [p for p in o["patterns"] if re.search(p, low)]
        if hits:
            out.append({"objection": k, "matched": hits, "score": len(hits)})
    return sorted(out, key=lambda x: -x["score"])


def handle_objection(text: str, context: dict | None = None) -> dict:
    """context: {"verified_proof": [str], "fit_issues": [str], "buyer_budget": n, "price": n, "context_type": str}"""
    ctx = context or {}
    matches = classify_objection(text)
    if not matches:
        return {"objection_text": text, "matches": [], "plan": {
            "first_step": "Clarify before responding: 'Can you tell me more about what's behind that?'",
            "note": "No known pattern matched; don't guess the objection."}}
    key = matches[0]["objection"]
    o = OBJECTIONS[key]
    decision, reasons = "clarify_then_respond", []
    if ctx.get("fit_issues"):
        decision, reasons = "consider_disqualifying", [f"Known fit issues: {ctx['fit_issues']}"]
    if key in ("price", "no_budget") and ctx.get("buyer_budget") is not None and ctx.get("price") is not None \
            and ctx["buyer_budget"] < 0.5 * ctx["price"]:
        decision, reasons = "offer_smaller_scope_or_disqualify", [f"Stated budget {ctx['buyer_budget']} is far below price {ctx['price']}"]
    proof = ctx.get("verified_proof") or []
    return {
        "objection_text": text, "matches": matches, "primary": key,
        "plan": {
            "possible_underlying_reasons": o["underlying"],
            "clarifying_questions": o["clarify"],
            "evidence_to_use": proof or [f"[NEEDED] {e}" for e in o["evidence"]],
            "truthful_response_pattern": o["response"],
            "stop_pursuing_if": o["walk_away"],
            "offer_unsuitable_when": o["unsuitable_when"],
            "improve_product_or_offer_if": o["improve_offer_if"],
            "decision": decision, "decision_reasons": reasons,
        },
        "rules": ["Ask before answering", "Never invent proof, discounts, deadlines or capabilities",
                  "Disqualifying a poor-fit buyer is a good outcome"],
    }


def qualify(lead: dict, criteria: dict | None = None, disqualifiers: list[str] | None = None) -> dict:
    """lead: {criterion: 0|1|2|None (unknown), ..., "flags": [str]}. 0=no, 1=partial, 2=strong."""
    criteria = criteria or DEFAULT_QUAL
    disq = set(disqualifiers or ["no_problem", "cannot_afford", "illegal_use", "bad_fit_confirmed"])
    hit_disq = [f for f in lead.get("flags", []) if f in disq]
    known, total_w, score, unknown = 0, 0.0, 0.0, []
    for k, c in criteria.items():
        v = lead.get(k)
        if v is None:
            unknown.append({"criterion": k, "ask": c["question"]})
            continue
        if v not in (0, 1, 2):
            raise ValueError(f"{k} must be 0, 1, 2 or None")
        known += 1
        total_w += c["weight"] * 2
        score += c["weight"] * v
    pct = score / total_w if total_w else 0.0
    if hit_disq or lead.get("fit") == 0 or lead.get("problem") == 0:
        status = "disqualify"
    elif known < len(criteria) / 2:
        status = "needs_discovery"
    elif pct >= 0.7:
        status = "qualified"
    elif pct >= 0.4:
        status = "nurture"
    else:
        status = "disqualify"
    return {"status": status, "score": round(pct, 2), "known_criteria": known, "unknown": unknown,
            "disqualifiers": hit_disq, "next_questions": [u["ask"] for u in unknown][:3]}


def discovery_questions(context_type: str = "software") -> dict:
    base = {k: list(v) for k, v in DISCOVERY["_common"].items()}
    for k, v in DISCOVERY.get(context_type, {}).items():
        base.setdefault(k, []).extend(v)
    return base


class ObjectionLog:
    """Persist real objections heard in calls, with outcome, to learn frequencies."""

    def __init__(self, store: KnowledgeStore):
        self.store = store

    def record(self, text: str, outcome: str, product: str | None = None, audience: str | None = None,
               source_ref: str = "sales_call") -> str:
        cls = classify_objection(text)
        rid, _ = self.store.add({
            "kind": "objection", "title": f"{(cls[0]['objection'] if cls else 'unclassified')}: {text[:120]}",
            "product": product, "audience": audience, "basis": "observed", "confidence": "medium",
            "tags": ["objection", cls[0]["objection"] if cls else "unclassified", outcome], "sources": [source_ref],
            "data": {"text": text, "classification": cls, "outcome": outcome}})
        return rid

    def frequencies(self, product: str | None = None) -> dict:
        recs = self.store.find(kind="objection", product=product)
        types = Counter((r["data"]["classification"] or [{"objection": "unclassified"}])[0]["objection"] for r in recs)
        outcomes = Counter((r["data"]["classification"][0]["objection"] if r["data"]["classification"] else "unclassified",
                            r["data"]["outcome"]) for r in recs)
        return {"total": len(recs), "by_type": dict(types.most_common()),
                "by_type_and_outcome": {f"{a}|{b}": n for (a, b), n in outcomes.items()}}
