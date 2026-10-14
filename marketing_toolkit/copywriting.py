"""Sales copy engine: frameworks, channel specs, draft skeletons, evaluation.

- FRAMEWORKS: 10 copy structures with section-by-section guidance.
- CHANNELS: configurable defaults for length limits per asset type
  (verify current platform limits before publishing; they change).
- build_draft(): assembles a structured skeleton from REAL inputs (offer,
  customer profile, verified proof). Missing facts become [PLACEHOLDER]s.
  Claude (or a human) writes the final prose; this guarantees structure and truthfulness.
- evaluate_copy(): scores 12 criteria (0-5), explains each weakness and how to
  fix it, runs channel limit checks and the QC gate.
"""

from __future__ import annotations

import re

from . import qc as QC
from . import text as T
from .config import load_config
from .offer import specificity
from .schemas import COPY_INPUT, validate

FRAMEWORKS: dict[str, dict] = {
    "pas": {"name": "Problem-Agitation-Solution", "best_for": ["problem_aware"], "sections": [
        ("problem", "Name the problem in the customer's exact words."),
        ("agitation", "Show the real consequence (time, money, risk, emotion) using observed evidence."),
        ("solution", "Introduce the offer as the mechanism that removes the problem."),
        ("proof", "One verified proof point."), ("cta", "One clear next step.")]},
    "aida": {"name": "Attention-Interest-Desire-Action", "best_for": ["unaware", "problem_aware"], "sections": [
        ("attention", "A specific, relevant hook (situation, number you can prove, or question)."),
        ("interest", "Why this matters to this reader now."),
        ("desire", "Outcome + proof + what's included."), ("action", "CTA with what happens next.")]},
    "bab": {"name": "Before-After-Bridge", "best_for": ["problem_aware", "solution_aware"], "sections": [
        ("before", "Their current situation, in their words."), ("after", "The realistic end state."),
        ("bridge", "How the offer gets them there."), ("cta", "Next step.")]},
    "fab": {"name": "Feature-to-Benefit", "best_for": ["product_aware"], "sections": [
        ("feature", "What it is/does (concrete)."), ("advantage", "Why that's better than the alternative."),
        ("benefit", "What the buyer gains (outcome)."), ("cta", "Next step.")]},
    "objection_led": {"name": "Objection-led", "best_for": ["product_aware", "solution_aware"], "sections": [
        ("objection", "State the top objection honestly."), ("reframe", "Truthful answer with evidence."),
        ("proof", "Verified proof that addresses it."), ("cta", "Low-risk next step.")]},
    "proof_led": {"name": "Proof-led", "best_for": ["product_aware", "most_aware"], "sections": [
        ("proof", "Lead with the strongest verified proof."), ("outcome", "What that means for the reader."),
        ("offer", "What they get."), ("cta", "Next step.")]},
    "comparison": {"name": "Comparison-led", "best_for": ["solution_aware"], "sections": [
        ("alternative", "Name the status quo or competitor category fairly."),
        ("difference", "The concrete, verifiable difference."), ("who_for", "Who should (and shouldn't) choose this."),
        ("cta", "Next step.")]},
    "story": {"name": "Story-led", "best_for": ["unaware", "problem_aware"], "sections": [
        ("character", "A real customer or founder situation (real, permissioned)."), ("conflict", "The problem they hit."),
        ("turning_point", "What changed (the offer/mechanism)."), ("resolution", "The actual result."), ("cta", "Next step.")]},
    "demonstration": {"name": "Demonstration-led", "best_for": ["solution_aware", "product_aware"], "sections": [
        ("setup", "The task the viewer recognises."), ("demo", "Show it being done with the product (steps/time)."),
        ("result", "The visible result."), ("cta", "Try it yourself.")]},
    "risk_reduction": {"name": "Risk-reduction", "best_for": ["product_aware", "most_aware"], "sections": [
        ("risk", "Name the perceived risk."), ("reversal", "The real risk reversal (trial, pilot, guarantee you honour)."),
        ("proof", "Evidence others succeeded."), ("cta", "Start with low commitment.")]},
}

# Defaults only - verify current platform limits before publishing.
CHANNELS: dict[str, dict] = {
    "google_rsa_headline": {"max_chars": 30}, "google_rsa_description": {"max_chars": 90},
    "meta_primary_text": {"soft_max_chars": 125}, "meta_headline": {"soft_max_chars": 40},
    "tiktok_ad_text": {"max_chars": 100}, "youtube_script_15s": {"max_words": 40}, "youtube_script_30s": {"max_words": 80},
    "app_store_title": {"max_chars": 30}, "app_store_subtitle": {"max_chars": 30}, "app_store_promo": {"max_chars": 170},
    "email_subject": {"soft_max_chars": 60}, "sms": {"max_chars": 160}, "x_post": {"max_chars": 280},
    "linkedin_post": {"soft_max_chars": 1300}, "landing_headline": {"soft_max_words": 14},
    "cold_email": {"soft_max_words": 125}, "push_notification": {"soft_max_chars": 110},
    "cta_button": {"soft_max_words": 5},
}
ASSET_TYPES = ["landing_page", "headline", "subheadline", "product_description", "app_store_listing", "sales_email",
               "cold_outreach", "follow_up", "direct_response_ad", "video_ad_script", "social_post", "cta",
               "sales_presentation", "onboarding_copy", "upgrade_prompt", "abandoned_cart", "win_back"]
JARGON = ["synergy", "leverage", "paradigm", "holistic", "robust", "scalable", "end-to-end", "best-of-breed",
          "ecosystem", "utilize", "facilitate", "omnichannel", "actionable insights", "bandwidth"]
EMOTION = ["frustrat", "stress", "worry", "relief", "confiden", "peace of mind", "embarrass", "proud", "tired of",
           "finally", "fear", "love", "hate", "annoy", "overwhelm"]


def recommend_framework(awareness: str | None, asset_type: str | None = None) -> list[str]:
    ranked = [k for k, v in FRAMEWORKS.items() if awareness in v["best_for"]] if awareness else []
    if asset_type in ("video_ad_script",):
        ranked = ["demonstration", "story"] + ranked
    if asset_type in ("upgrade_prompt", "abandoned_cart"):
        ranked = ["risk_reduction", "fab"] + ranked
    return list(dict.fromkeys(ranked or ["pas", "bab", "proof_led"]))


def build_draft(framework: str, brief: dict) -> dict:
    """brief: {offer: {...}, pains: [str], outcomes: [str], objections: [str],
    proof: [{"text", "verified": bool, "source_ref"}], customer_terms: [str],
    channel, asset_type, tone, awareness, cta}"""
    if framework not in FRAMEWORKS:
        raise ValueError(f"unknown framework {framework}; choose from {list(FRAMEWORKS)}")
    offer = brief.get("offer", {}) or {}
    proof = [p for p in brief.get("proof", []) if p.get("verified")]
    pains, outs, objs = brief.get("pains", []), brief.get("outcomes", []), brief.get("objections", [])

    def first(lst, ph):
        return lst[0] if lst else f"[{ph}]"
    fill = {
        "problem": first(pains, "PAIN IN CUSTOMER WORDS"), "before": first(pains, "CURRENT SITUATION"),
        "agitation": f"[CONSEQUENCE OF: {first(pains, 'PAIN')} - use evidence]",
        "solution": offer.get("value_proposition") or f"{offer.get('name', '[OFFER]')}: [MECHANISM]",
        "bridge": offer.get("value_proposition") or "[HOW THE OFFER GETS THEM THERE]",
        "after": first(outs, "REALISTIC OUTCOME"), "outcome": first(outs, "OUTCOME"), "benefit": first(outs, "BENEFIT"),
        "desire": first(outs, "OUTCOME") + " + [PROOF] + [WHAT'S INCLUDED]",
        "proof": proof[0]["text"] if proof else "[VERIFIED PROOF - none supplied, do not invent]",
        "objection": first(objs, "TOP OBJECTION"), "risk": first(objs, "PERCEIVED RISK"),
        "reframe": "[TRUTHFUL ANSWER + EVIDENCE]",
        "reversal": offer.get("risk_reversal") if offer.get("guarantee_terms_verified") else "[RISK REVERSAL - only if verified]",
        "offer": ", ".join(offer.get("deliverables", [])) or "[WHAT THEY GET]",
        "feature": (offer.get("deliverables") or ["[FEATURE]"])[0], "advantage": offer.get("differentiation") or "[ADVANTAGE VS ALTERNATIVE]",
        "alternative": (offer.get("alternatives") or ["[STATUS QUO / ALTERNATIVE]"])[0],
        "difference": offer.get("differentiation") or "[VERIFIABLE DIFFERENCE]",
        "who_for": offer.get("target_customer") or "[WHO IT'S FOR / NOT FOR]",
        "cta": brief.get("cta") or "[ONE ACTION + WHAT HAPPENS NEXT]", "action": brief.get("cta") or "[ONE ACTION]",
        "attention": f"[HOOK about: {first(pains, 'PAIN')}]", "interest": "[WHY NOW, FOR THIS READER]",
        "character": "[REAL, PERMISSIONED CUSTOMER/FOUNDER STORY]", "conflict": first(pains, "PROBLEM"),
        "turning_point": offer.get("name", "[OFFER]"), "resolution": "[ACTUAL RESULT - verified]",
        "setup": first(pains, "TASK"), "demo": "[SHOW STEPS / TIME]", "result": first(outs, "VISIBLE RESULT"),
    }
    sections = [{"section": s, "guidance": g, "draft": fill.get(s, f"[{s.upper()}]")} for s, g in FRAMEWORKS[framework]["sections"]]
    placeholders = sorted({m for s in sections for m in re.findall(r"\[[^\]]+\]", s["draft"])})
    ch = brief.get("channel")
    return {"framework": framework, "framework_name": FRAMEWORKS[framework]["name"], "asset_type": brief.get("asset_type"),
            "channel": ch, "channel_limits": CHANNELS.get(ch, {}), "tone": brief.get("tone", "plain, specific, confident"),
            "customer_terms_to_use": brief.get("customer_terms", [])[:8], "sections": sections,
            "placeholders": placeholders,
            "instructions": "Write final prose section by section. Keep every fact traceable; leave or remove placeholders, never invent them. Run evaluate_copy() after writing."}


def _crit(name, score, why, fix):
    return {"criterion": name, "score": round(max(0, min(5, score)), 2), "why": why, "how_to_improve": fix if score < 4 else ""}


def channel_check(text: str, channel: str | None) -> list[str]:
    spec = CHANNELS.get(channel or "", {})
    issues, n_chars, n_words = [], len(text), len(T.words(text))
    for k, v in spec.items():
        if k == "max_chars" and n_chars > v:
            issues.append(f"{n_chars} chars exceeds hard limit {v} for {channel}")
        if k == "soft_max_chars" and n_chars > v:
            issues.append(f"{n_chars} chars exceeds recommended {v} for {channel} (may be truncated)")
        if k in ("max_words", "soft_max_words") and n_words > v:
            issues.append(f"{n_words} words exceeds {'limit' if k == 'max_words' else 'recommended'} {v} for {channel}")
    return issues


def evaluate_copy(inp: dict, config: dict | None = None) -> dict:
    validate(inp, COPY_INPUT)
    cfg = load_config(config)
    text = inp["text"]
    low = text.lower()
    offer = inp.get("offer") or {}
    sents = T.sentences(text)
    opening = " ".join(sents[:2])
    rd = T.readability(text)
    qc_ctx = {"kind": inp.get("kind", "copy"), "substantiated_claims": inp.get("substantiated_claims", []),
              "testimonial_ids": inp.get("evidence_ids", []), "audience_terms": inp.get("audience_terms", []),
              "urgency_is_real": offer.get("urgency_is_real", False),
              "risk_reversal_verified": offer.get("guarantee_terms_verified", False)}
    qc = QC.evaluate(text, qc_ctx, config)
    codes = {f["code"] for f in qc["findings"]}
    c = []

    terms = inp.get("audience_terms") or []
    used = T.contains_any(text, terms) if terms else []
    you = len(re.findall(r"\byou(r|'re|rs)?\b", low))
    we = len(re.findall(r"\b(we|our|us)\b", low))
    ar = (2 + 3 * min(1, len(used) / max(1, min(3, len(terms))))) if terms else (3.5 if you >= we else 2.5)
    c.append(_crit("audience_relevance", ar, f"uses {len(used)}/{len(terms)} customer terms; 'you' {you} vs 'we' {we}",
                   "Use the customer's own words (from VoC) and write about them, not about yourself."))

    grade = rd["grade"] or 0
    cl = 5 - max(0, (grade - 8) * 0.5) - 0.5 * len(T.contains_any(text, JARGON)) - (1 if rd["avg_sentence_words"] > 22 else 0)
    c.append(_crit("clarity", cl, f"grade {rd['grade']}, avg sentence {rd['avg_sentence_words']} words, jargon {T.contains_any(text, JARGON)}",
                   "Shorter sentences, plain words, one idea per sentence; cut jargon."))

    spc = specificity(text[:600])
    c.append(_crit("specificity", 5 * spc, f"specificity index {spc:.2f}",
                   "Add concrete details: who, what exactly, how long, how much (only verifiable facts)."))

    cred = 4 - (2 if "unsupported_claim" in codes else 0) - (2 if "fabricated_testimonial" in codes else 0) \
        - (1 if "unrealistic_promise" in codes else 0) + (1 if inp.get("substantiated_claims") or inp.get("evidence_ids") else 0)
    c.append(_crit("credibility", cred, "penalised for unsupported claims/testimonials/promises" if cred < 4 else "claims are backed or modest",
                   "Back every claim with evidence or soften it; remove anything you can't prove."))

    vp_terms = set(T.content_words(" ".join([offer.get("value_proposition", ""), offer.get("desired_outcome", "")])))
    vp_hit = len(vp_terms & set(T.content_words(opening))) / max(1, len(vp_terms)) if vp_terms else None
    vps = (1.5 + 3.5 * min(1, vp_hit * 2)) if vp_hit is not None else (3 if spc > 0.5 else 2)
    c.append(_crit("value_proposition", vps, "outcome stated in opening" if vps >= 4 else "core value not clear in first two sentences",
                   "State the outcome for this customer in the first line."))

    diff = any(re.search(p, low) for p in QC.DIFF_SIGNALS) or any(a.lower() in low for a in offer.get("alternatives", []))
    c.append(_crit("differentiation", 4.5 if diff else 2, "contrast with alternatives present" if diff else "no contrast with alternatives",
                   "Name what they do today and why this is better in one concrete way."))

    emo = T.contains_any(text, EMOTION) or [w for w in EMOTION if w in low]
    c.append(_crit("emotional_relevance", 4 if emo else 2.5, f"emotional cues: {emo[:4]}",
                   "Reflect the feeling customers describe (from VoC), without exaggeration."))

    proof_sig = [p for p in QC.PROOF_SIGNALS if re.search(p, low)]
    pr = (2 + (2 if inp.get("evidence_ids") else 0) + (1 if proof_sig else 0)) if proof_sig or inp.get("evidence_ids") else 0.5
    c.append(_crit("proof", pr, f"proof signals {len(proof_sig)}, verified evidence ids {len(inp.get('evidence_ids', []))}",
                   "Add one verified proof element near the claim it supports."))

    objs = inp.get("known_objections") or []
    covered = [o for o in objs if len(set(T.content_words(o)) & set(T.content_words(text))) >= max(1, len(T.content_words(o)) // 2)]
    oc = (1 + 4 * len(covered) / len(objs)) if objs else 3
    c.append(_crit("objection_coverage", oc, f"addresses {len(covered)}/{len(objs)} known objections" if objs else "no objections supplied",
                   "Answer the top objection explicitly (price, trust, effort, timing)."))

    fl = rd["flesch"] if rd["flesch"] is not None else 0
    c.append(_crit("readability", 5 if fl >= 60 else 4 if fl >= 50 else 3 if fl >= 40 else 2 if fl >= 30 else 1,
                   f"Flesch reading ease {fl}", "Aim for Flesch 60+: shorter words and sentences."))

    ctas = T.contains_any(text, QC.CTA_VERBS)
    end_cta = bool(T.contains_any(" ".join(sents[-2:]), QC.CTA_VERBS)) if sents else False
    c.append(_crit("cta", 5 if ctas and end_cta else 3 if ctas else 0.5, f"CTA verbs {ctas[:4]}, CTA at end: {end_cta}",
                   "Finish with one specific action and what happens after the click."))

    cons, issues = 5.0, []
    if offer.get("price") is not None:
        prices = [float(p.replace(",", "")) for p in re.findall(r"[$€£]\s?(\d[\d,]*(?:\.\d+)?)", text)]
        if prices and all(abs(p - float(offer["price"])) > 0.01 for p in prices):
            cons -= 3
            issues.append(f"price in copy {prices} differs from offer price {offer['price']}")
    if offer and T.contains_any(text, ["free"]) and offer.get("billing") not in ("free",) and "trial" not in low:
        cons -= 1.5
        issues.append("copy says 'free' but offer is not free")
    c.append(_crit("offer_consistency", cons, "; ".join(issues) or "consistent with offer", "Make price, terms and inclusions match the actual offer exactly."))

    w = cfg["copy_weights"]
    for x in c:
        x["weight"] = w.get(x["criterion"], 1.0)
    overall = sum(x["score"] * x["weight"] for x in c) / sum(x["weight"] for x in c)
    limits = channel_check(text, inp.get("channel"))
    hard = [i for i in limits if "hard limit" in i or "exceeds limit" in i]
    passed = overall >= cfg["copy_pass_score"] and qc["decision"] != "reject" and not hard
    return {"overall": round(overall, 2), "pass_threshold": cfg["copy_pass_score"], "passed": passed,
            "criteria": c, "readability": rd, "channel_issues": limits, "qc": qc,
            "priority_fixes": [{"criterion": x["criterion"], "fix": x["how_to_improve"], "why": x["why"]}
                               for x in sorted(c, key=lambda x: (x["score"] - 5) * x["weight"]) if x["how_to_improve"]][:5],
            "note": "Heuristic quality score. Real performance must be measured (see experiments)."}


def to_record(text: str, evaluation: dict, asset_type: str, product: str | None = None, audience: str | None = None,
              framework: str | None = None) -> dict:
    return {"kind": "copy_asset", "title": f"{asset_type}: {text[:80]}"[:300], "product": product, "audience": audience,
            "basis": "hypothesis", "confidence": "low", "tags": ["copy", asset_type] + ([framework] if framework else []),
            "data": {"text": text, "asset_type": asset_type, "framework": framework,
                     "score": evaluation["overall"], "passed": evaluation["passed"], "qc_decision": evaluation["qc"]["decision"]}}
