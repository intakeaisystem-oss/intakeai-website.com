"""Marketing quality control: the gate every output passes before it is "done".

evaluate(text, context) detects generic messaging, unsupported claims,
fabricated testimonials, misleading scarcity, unrealistic promises,
platform-policy risks, missing proof, unclear CTAs, weak differentiation,
poor audience fit, confusing offers, repeated concepts, ad/landing mismatch
and missing measurement plans.

Every finding says what is wrong, why it matters and what to change.
Decision: reject (any finding whose code is in config.qc_reject_on),
revise (warnings above config.qc_max_warnings) or approve.
An internal QC pass is NOT evidence of real-world performance, and policy flags
are heuristics, not an official platform review.
"""

from __future__ import annotations

import re

from . import text as T
from .config import load_config
from .offer import HYPE_WORDS, specificity

GENERIC_PHRASES = [
    "take your business to the next level", "next level", "unlock your potential", "we help businesses",
    "solutions for", "one-stop shop", "high quality", "best in class", "world class", "innovative solution",
    "empower", "leverage", "synergy", "cutting-edge", "seamless experience", "your success is our priority",
    "we are passionate", "trusted partner", "tailored solutions", "transform your", "all-in-one solution",
    "dream", "skyrocket", "boost your business",
]
SUPERLATIVES = ["best", "fastest", "cheapest", "leading", "#1", "number one", "most popular", "most trusted",
                "top-rated", "top rated", "only solution", "proven", "clinically", "scientifically", "guaranteed",
                "award-winning", "lowest price"]
SCARCITY = [r"only \d+ (left|spots?|seats?|places?)", r"limited time", r"ends (tonight|today|soon|at midnight)",
            r"last chance", r"spots? (are )?(filling|left)", r"while (stocks?|supplies) last", r"act now",
            r"hurry", r"countdown", r"before it'?s gone", r"price goes up (tomorrow|tonight)", r"today only"]
UNREALISTIC = [r"overnight", r"guaranteed (results|income|success|sales|leads)", r"get rich", r"100% (success|guaranteed)",
               r"risk[- ]free", r"instantly", r"never (worry|again)", r"(double|triple|10x) your (revenue|income|sales|traffic)",
               r"zero effort", r"effortless(ly)?", r"passive income", r"works for everyone", r"in just \d+ (minutes|days) a"]
POLICY = {
    "personal_attributes": (r"\b(are you|you'?re|you are|your)\b[^.?!]{0,30}\b(diabetic|depressed|overweight|fat|gay|lesbian|"
                            r"christian|muslim|jewish|bankrupt|in debt|divorced|disabled|pregnant|addict|anxious|black|hispanic|"
                            r"over \d\d|single)\b", "high",
                            "Ads that assert or imply a viewer's personal attributes (health, finances, religion, etc.) are commonly prohibited (e.g. Meta)."),
    "health_claims": (r"\b(cure[sd]?|heal[s]?|treat[s]?|prevent[s]?) (cancer|diabetes|anxiety|depression|disease|covid)|"
                      r"lose \d+ ?(lbs|pounds|kg) in \d+|miracle", "high",
                      "Health and weight-loss claims face strict review and legal substantiation requirements."),
    "financial_claims": (r"\b(guaranteed|risk[- ]free) (return|profit|income)|make \$?\d[\d,]* (a|per) (day|week|month)|"
                         r"get out of debt fast", "high",
                         "Income/financial claims are restricted and legally sensitive."),
    "before_after": (r"before (and|&) after|before/after", "medium",
                     "Before/after imagery or claims are restricted for health/cosmetic categories on major platforms."),
    "sensational": (r"\b(shocking|you won'?t believe|doctors hate|this one trick|secret they don'?t want)\b", "medium",
                    "Sensational/clickbait language is low-quality and often disapproved."),
    "fake_ui": (r"\b(click (here )?to (play|download)|you have \(?\d+\)? new message|system alert)\b", "high",
                "Fake buttons/notifications are prohibited deceptive design."),
}
CTA_VERBS = ["get", "start", "try", "book", "buy", "shop", "order", "download", "join", "sign up", "subscribe",
             "claim", "schedule", "request", "call", "contact", "learn more", "see", "discover", "apply", "reserve",
             "install", "register", "save", "compare", "watch", "talk to"]
PROOF_SIGNALS = [r"\breviews?\b", r"\brated\b", r"\bcase stud", r"\bcustomers?\b", r"\btestimonial", r"\d+(\.\d+)?/5",
                 r"\bstars?\b", r"\bused by\b", r"\btrusted by\b", r"\bdata\b", r"\bresults?\b", r"\bdemo\b", r"\bcertified\b"]
DIFF_SIGNALS = [r"\bunlike\b", r"\binstead of\b", r"\bwithout\b", r"\bonly\b", r"\bvs\.?\b", r"\bcompared\b", r"\bno more\b",
                r"\bnot another\b", r"\bdifferent\b"]


def _find(code, severity, message, why, fix, evidence=None):
    return {"code": code, "severity": severity, "message": message, "why_it_matters": why, "fix": fix,
            "evidence": evidence or []}


def _substantiated(snippet: str, substantiated: list[str]) -> bool:
    low = snippet.lower()
    return any(s.lower() in low or low in s.lower() for s in substantiated if s)


def evaluate(text: str, context: dict | None = None, config: dict | None = None) -> dict:
    """context keys (all optional):
    platform, kind ('ad'|'landing'|'email'|'copy'...), substantiated_claims [str],
    testimonial_ids [str] (verified testimonials in use), urgency_is_real bool,
    risk_reversal_verified bool, audience_terms [str], landing_text str,
    other_concepts [str], measurement_plan dict, require_measurement bool, require_cta bool (default True)."""
    ctx = context or {}
    cfg = load_config(config)
    low = text.lower()
    f: list[dict] = []
    subs = ctx.get("substantiated_claims", [])

    gen = T.contains_any(text, GENERIC_PHRASES) + T.contains_any(text, HYPE_WORDS)
    if gen or specificity(text[:400]) < 0.35:
        f.append(_find("generic_messaging", "warn", "Generic or vague messaging",
                       "Generic lines are interchangeable with competitors and give the buyer no reason to believe or act.",
                       "Replace with a concrete outcome, a specific customer, a number you can prove, or the customer's own words.",
                       sorted(set(gen))))

    claims = []
    for s in T.sentences(text):
        sl = s.lower()
        numeric = re.search(r"\d+(\.\d+)?\s?(%|x\b|times|percent)|(increase|grow|boost|cut|reduce|save)[a-z]* [^.]{0,30}\bby\b"
                            r"|\d(\.\d)?\s?/\s?5|\d+(\.\d)? stars?|\b\d[\d,]*\+? (happy |satisfied )?(customers|users|clients|businesses|"
                            r"owners|companies|reviews|downloads|members|teams)", sl)
        sup = T.contains_any(s, SUPERLATIVES)
        if (numeric or sup) and not _substantiated(s, subs):
            claims.append(s.strip())
    if claims:
        f.append(_find("unsupported_claim", "reject", f"{len(claims)} claim(s) without substantiation",
                       "Unsubstantiated performance or superiority claims mislead buyers, break advertising law (e.g. FTC/ASA rules) and get ads rejected.",
                       "Add the evidence to context.substantiated_claims (and keep the source), soften to a verifiable statement, or remove.",
                       claims[:5]))

    testimonial_like = re.findall(r"[\"“][^\"”]{12,}[\"”]\s*(?:[-–—]\s*[A-Z][a-z]+|,? said)", text)
    if testimonial_like and not ctx.get("testimonial_ids"):
        f.append(_find("fabricated_testimonial", "reject", "Testimonial-style quote without a verified testimonial ID",
                       "Invented or unverified testimonials are deceptive and illegal in many jurisdictions.",
                       "Use only real, permissioned testimonials and pass their IDs in context.testimonial_ids; otherwise remove.",
                       testimonial_like[:3]))
    if re.search(r"\b(john|jane) (d|doe|smith)\b|\blorem ipsum\b|\[testimonial\]", low):
        f.append(_find("fabricated_testimonial", "reject", "Placeholder testimonial/name found",
                       "Placeholder social proof looks fabricated if published.", "Replace with a verified testimonial or remove."))

    scar = [m.group(0) for p in SCARCITY for m in [re.search(p, low)] if m]
    if scar and not ctx.get("urgency_is_real"):
        f.append(_find("misleading_scarcity", "reject", "Scarcity/urgency language without confirmed real constraint",
                       "Fake urgency erodes trust and can breach consumer-protection rules.",
                       "Only use a real deadline or capacity limit (set context.urgency_is_real=True once confirmed) or replace with a genuine reason to act now.",
                       scar))

    unreal = [m.group(0) for p in UNREALISTIC for m in [re.search(p, low)] if m]
    if ctx.get("risk_reversal_verified"):
        unreal = [u for u in unreal if not re.match(r"risk[- ]free", u)]
    if unreal:
        f.append(_find("unrealistic_promise", "reject", "Unrealistic or absolute promise",
                       "Absolute promises set expectations you cannot guarantee, cause refunds and trigger ad disapproval.",
                       "State the typical, evidenced outcome and conditions instead.", unreal))

    for code, (pat, sev, why) in POLICY.items():
        m = re.search(pat, low)
        if m:
            f.append(_find("policy_risk_high" if sev == "high" else "policy_risk", "reject" if sev == "high" else "warn",
                           f"Possible platform-policy issue: {code}", why + " (heuristic flag, verify against the platform's current policy)",
                           "Rewrite without the flagged pattern; check the platform's advertising policies before launch.", [m.group(0)]))

    kind = ctx.get("kind", "copy")
    if kind in ("ad", "landing", "sales_page", "email") and not any(re.search(p, low) for p in PROOF_SIGNALS):
        f.append(_find("missing_proof", "warn", "No proof element",
                       "Buyers discount claims without evidence; proof near the ask reduces perceived risk.",
                       "Add one verified proof item: review rating, real customer quote, data point, demo or guarantee you honour."))

    if ctx.get("require_cta", True):
        ctas = T.contains_any(text, CTA_VERBS)
        if not ctas:
            f.append(_find("unclear_cta", "warn", "No clear call to action",
                           "Without a specific next step, interested readers do nothing.",
                           "End with one action verb + what happens next (e.g. 'Book a 15-minute demo')."))
        elif len(set(ctas)) >= 5 and kind == "ad":
            f.append(_find("unclear_cta", "warn", "Many competing calls to action",
                           "Multiple asks split attention.", "Keep one primary CTA.", sorted(set(ctas))))

    if kind in ("ad", "landing", "sales_page") and not any(re.search(p, low) for p in DIFF_SIGNALS) and specificity(text) < 0.6:
        f.append(_find("weak_differentiation", "warn", "No differentiation from alternatives",
                       "If the buyer can't see why this beats what they do now, they default to the status quo.",
                       "Name the alternative and the concrete difference (speed, cost, effort, risk)."))

    terms = ctx.get("audience_terms") or []
    if terms and not T.contains_any(text, terms):
        f.append(_find("poor_audience_fit", "warn", "None of the audience's own terms are used",
                       "Copy that doesn't use the customer's language feels written for someone else.",
                       f"Work in customer terms such as: {terms[:5]}"))

    prices = re.findall(r"[$€£]\s?\d[\d,.]*", text)
    long_sents = [s for s in T.sentences(text) if len(T.words(s)) > 35]
    if len(set(prices)) > 3 or len(long_sents) > 2:
        f.append(_find("confusing_offer", "warn", "Offer may be confusing (many prices or very long sentences)",
                       "Confusion kills conversion: buyers who can't quickly understand the deal leave.",
                       "One price/plan per message, short sentences, state exactly what they get.",
                       (prices[:5] + [s[:60] for s in long_sents[:2]])))

    others = ctx.get("other_concepts") or []
    sims = [(round(T.similarity(text, o), 2), o[:60]) for o in others]
    rep = [s for s in sims if s[0] >= cfg["concept_similarity_threshold"]]
    if rep:
        f.append(_find("repeated_concept", "warn", "Too similar to an existing concept",
                       "Near-duplicate creatives waste test budget and teach you nothing new.",
                       "Change the angle (problem vs proof vs demo vs comparison), not just the wording.",
                       [f"similarity {s}: {o}" for s, o in rep]))

    landing = ctx.get("landing_text")
    if landing:
        promise = set(T.content_words(" ".join(T.sentences(text)[:2])))
        page_words = set(T.content_words(landing))
        overlap = len(promise & page_words) / max(1, len(promise))
        if overlap < 0.4:
            f.append(_find("message_mismatch", "warn", f"Ad promise poorly reflected on landing page (overlap {overlap:.0%})",
                           "When the page doesn't continue the ad's promise, visitors feel misled and bounce.",
                           "Echo the ad's headline/promise in the landing hero; keep offer, price and imagery consistent.",
                           sorted(promise - page_words)[:10]))

    if ctx.get("require_measurement"):
        plan = ctx.get("measurement_plan") or {}
        if not plan.get("primary_metric"):
            f.append(_find("missing_measurement_plan", "warn", "No measurement plan (primary metric missing)",
                           "Without a pre-defined metric you can't tell if this worked or learn from it.",
                           "Define primary metric, guardrails, tracking events and decision rule before launch."))

    rejects = [x for x in f if x["severity"] == "reject" and x["code"] in cfg["qc_reject_on"]]
    warns = [x for x in f if x["severity"] != "reject" or x["code"] not in cfg["qc_reject_on"]]
    decision = "reject" if rejects else "revise" if len(warns) > cfg["qc_max_warnings"] else "approve"
    return {"decision": decision, "passed": decision == "approve", "findings": f,
            "counts": {"reject": len(rejects), "warn": len(warns)},
            "note": "Internal quality gate. Passing it does not prove real-world performance or policy compliance."}
