"""Offer engineering: configurable offer scoring + offer structure generator.

score_offer() rates 15 criteria (0-5), explains each weakness and the fix,
and checks seller economics. Scores are heuristic quality checks of the
offer *definition*, not predictions of market performance.

generate_structures() proposes alternative offer structures for different
awareness levels and buying situations using only facts present in the offer;
anything missing is left as an explicit [PLACEHOLDER], never invented.
"""

from __future__ import annotations

import re

from . import text as T
from .config import load_config
from .schemas import AWARENESS, OFFER, validate

HYPE_WORDS = ["revolutionary", "game-changing", "game changing", "best in the industry", "best-in-class",
              "world-class", "cutting-edge", "cutting edge", "next-generation", "next level", "unparalleled",
              "ultimate", "unbeatable", "industry-leading", "groundbreaking", "disruptive", "seamless",
              "synergy", "state-of-the-art", "#1", "number one", "best ever", "magic", "insane results"]
GENERIC_AUDIENCE = ["everyone", "anyone", "all businesses", "businesses", "people", "customers", "users",
                    "small businesses", "companies", "entrepreneurs"]
VAGUE_OUTCOME = ["success", "growth", "better results", "more", "improve", "optimize", "transform", "level up"]


def specificity(text: str) -> float:
    """0-1 heuristic: numbers, units, concrete words up; hype/vague words down."""
    if not text:
        return 0.0
    s = 0.4
    if re.search(r"\d", text):
        s += 0.25
    if re.search(r"\b(minutes?|hours?|days?|weeks?|months?|%|percent|\$|€|£)\b|[$€£%]", text.lower()):
        s += 0.15
    n = len(T.words(text))
    s += 0.1 if 6 <= n <= 30 else -0.1
    s -= 0.2 * len(T.contains_any(text, HYPE_WORDS))
    s -= 0.1 * len(T.contains_any(text, VAGUE_OUTCOME))
    return max(0.0, min(1.0, s))


def _crit(name, score, issues=None, fixes=None):
    return {"criterion": name, "score": round(max(0, min(5, score)), 2), "issues": issues or [], "fixes": fixes or []}


def economics(offer: dict) -> dict:
    price, cost = offer.get("price"), offer.get("fulfillment_cost")
    cac, n = offer.get("acquisition_cost_estimate"), offer.get("expected_purchases_per_customer") or 1
    out = {"price": price, "fulfillment_cost": cost, "cac": cac, "purchases_per_customer": n}
    if price is None or cost is None:
        out["status"] = "unknown"
        return out
    gp = price - cost
    out["gross_profit_per_purchase"] = round(gp, 2)
    out["gross_margin"] = round(gp / price, 3) if price else None
    out["gross_profit_per_customer"] = round(gp * n, 2)
    if cac is not None:
        out["profit_after_cac"] = round(gp * n - cac, 2)
        out["ltv_to_cac"] = round(gp * n / cac, 2) if cac else None
    out["status"] = "computed"
    return out


def score_offer(offer: dict, config: dict | None = None) -> dict:
    validate(offer, OFFER)
    cfg = load_config(config)
    w = cfg["offer_weights"]
    c = []

    tc = offer.get("target_customer", "")
    if not tc:
        c.append(_crit("target_customer", 0, ["No target customer defined"], ["Name the segment: who, size/situation, and the trigger moment"]))
    elif tc.lower().strip() in GENERIC_AUDIENCE or len(T.words(tc)) < 3:
        c.append(_crit("target_customer", 2, ["Target customer is generic"], ["Narrow it: role + context + qualifier (e.g. 'owner-operators of 2-10 truck HVAC companies')"]))
    else:
        c.append(_crit("target_customer", 4 + (1 if re.search(r"\d", tc) else 0)))

    pr = offer.get("problem", "")
    sp = specificity(pr)
    c.append(_crit("problem", 0 if not pr else 1 + 4 * sp,
                   [] if pr and sp >= 0.6 else ["Problem missing or vague"],
                   [] if pr and sp >= 0.6 else ["State the problem in the customer's words with a concrete consequence (time, money, risk)"]))

    oc = offer.get("desired_outcome", "")
    so = specificity(oc)
    c.append(_crit("outcome", 0 if not oc else 1 + 4 * so,
                   [] if oc and so >= 0.6 else ["Outcome missing or not measurable"],
                   [] if oc and so >= 0.6 else ["Describe the end state the buyer can check: what changes, by how much, by when (only if you can deliver it)"]))

    vp = offer.get("value_proposition", "")
    hype = T.contains_any(" ".join([vp, offer.get("differentiation", "")]), HYPE_WORDS)
    sv = specificity(vp)
    c.append(_crit("value_proposition", 0 if not vp else 1 + 4 * sv,
                   (["Value proposition missing"] if not vp else []) + ([f"Unsupported hype words: {hype}"] if hype else []),
                   (["Write: [outcome] for [customer] without [main pain/cost]"] if not vp else []) +
                   (["Replace hype with a specific, provable claim"] if hype else [])))

    df = offer.get("differentiation", "")
    if not df:
        c.append(_crit("differentiation", 0, ["No differentiation stated"], ["Explain why this beats the main alternative for this customer"]))
    elif hype and specificity(df) < 0.5:
        c.append(_crit("differentiation", 1, ["Differentiation relies on superlatives"], ["Name the concrete difference vs a named alternative"]))
    else:
        ref = any(a.lower() in df.lower() for a in offer.get("alternatives", [])) or re.search(r"\b(unlike|instead of|vs\.?|only|without)\b", df.lower())
        c.append(_crit("differentiation", 4 + (1 if ref else 0)))

    price, billing = offer.get("price"), offer.get("billing")
    if price is None and billing != "free":
        c.append(_crit("pricing", 0, ["No price set"], ["Set a price (or a range) and billing model"]))
    else:
        c.append(_crit("pricing", 4 if billing else 3, [] if billing else ["Billing model missing"], [] if billing else ["Specify one-time / monthly / annual etc."]))

    c.append(_crit("packaging", 3.5 if offer.get("packaging") else 1.5,
                   [] if offer.get("packaging") else ["Packaging not described"],
                   [] if offer.get("packaging") else ["Describe tiers/what is included at each price point"]))

    dl = offer.get("deliverables", [])
    if not dl:
        c.append(_crit("deliverables", 0, ["No deliverables listed"], ["List what the buyer concretely receives"]))
    elif len(dl) > 10:
        c.append(_crit("deliverables", 3, ["Too many deliverables can dilute value"], ["Group into 3-5 outcome-based bundles"]))
    else:
        c.append(_crit("deliverables", 3 if len(dl) <= 2 else 5))

    ttv = offer.get("time_to_value_days")
    ttv_score = 1 if ttv is None else 5 if ttv <= 1 else 4 if ttv <= 7 else 3 if ttv <= 30 else 2 if ttv <= 90 else 1
    c.append(_crit("time_to_value", ttv_score, [] if ttv_score >= 3 else ["Slow or unknown time to first value"],
                   [] if ttv_score >= 3 else ["Add a quick first win (setup call, template, first result in week 1)"]))

    rr = offer.get("risk_reversal")
    if not rr:
        c.append(_crit("risk_reversal", 2, ["No risk reversal"], ["Consider a trial, pilot, milestone billing or a guarantee you can honour (legal review)"]))
    elif not offer.get("guarantee_terms_verified"):
        c.append(_crit("risk_reversal", 1, ["Guarantee/risk reversal not confirmed as commercially and legally feasible"],
                       ["Confirm terms, conditions and cost of honouring it before publishing"]))
    else:
        c.append(_crit("risk_reversal", 5))

    proofs = offer.get("proof", [])
    verified = [p for p in proofs if p.get("verified")]
    unverified = [p for p in proofs if not p.get("verified")]
    pscore = 0 if not verified else 3 if len(verified) == 1 else 4 if len({p["type"] for p in verified}) < 3 else 5
    pissues = ([] if verified else ["No verified proof"]) + ([f"{len(unverified)} unverified proof item(s) must not be used"] if unverified else [])
    c.append(_crit("proof", pscore, pissues, ([] if verified else ["Collect real reviews, case data, a demo or a pilot result"]) +
                   (["Verify or remove unverified proof"] if unverified else [])))

    if offer.get("urgency_reason"):
        if offer.get("urgency_is_real"):
            c.append(_crit("urgency", 5))
        else:
            c.append(_crit("urgency", 0, ["Urgency reason not confirmed as real: misleading scarcity risk"],
                           ["Use only real deadlines/capacity limits, or remove urgency"]))
    else:
        c.append(_crit("urgency", 3, ["No reason to act now"], ["Tie timing to a real event in the buyer's world (season, deadline, cost of delay)"]))

    eff = offer.get("implementation_effort")
    c.append(_crit("friction", {"none": 5, "low": 4, "medium": 3, "high": 1}.get(eff, 2.5),
                   [] if eff in ("none", "low") else ["Implementation effort high or unknown"],
                   [] if eff in ("none", "low") else ["Offer done-for-you setup, templates or onboarding to cut effort"]))

    alts = offer.get("alternatives", [])
    c.append(_crit("alternatives", 1 if not alts else 4, [] if alts else ["Competitive alternatives not listed"],
                   [] if alts else ["List what the buyer would do instead (competitors, DIY, hire, do nothing)"]))

    econ = economics(offer)
    if econ["status"] == "unknown":
        c.append(_crit("economics", 1, ["Seller economics unknown (price or fulfillment cost missing)"],
                       ["Add fulfillment_cost and acquisition_cost_estimate to check viability"]))
    else:
        ratio, gm = econ.get("ltv_to_cac"), econ.get("gross_margin") or 0
        if gm <= 0:
            c.append(_crit("economics", 0, ["Negative or zero gross margin"], ["Raise price, cut fulfillment cost, or change packaging"]))
        elif ratio is None:
            c.append(_crit("economics", 3 if gm >= 0.5 else 2, ["Acquisition cost unknown"], ["Estimate CAC to confirm the offer is profitable to sell"]))
        else:
            sc = 5 if ratio >= 3 else 4 if ratio >= 2 else 2 if ratio >= 1 else 0
            c.append(_crit("economics", sc, [] if ratio >= 2 else [f"Gross profit per customer / CAC = {ratio}"],
                           [] if ratio >= 2 else ["Increase lifetime value (retention, upsell) or reduce CAC before scaling"]))

    total_w = sum(w.get(x["criterion"], 1.0) for x in c)
    overall = sum(x["score"] * w.get(x["criterion"], 1.0) for x in c) / total_w
    for x in c:
        x["weight"] = w.get(x["criterion"], 1.0)
    weakest = sorted([x for x in c if x["issues"]], key=lambda x: (x["score"] - 5) * x["weight"])
    blockers = [x["criterion"] for x in c if x["criterion"] in ("proof", "urgency", "risk_reversal", "economics") and x["score"] == 0]
    return {
        "offer": offer.get("name"), "overall": round(overall, 2), "pass_threshold": cfg["offer_pass_score"],
        "passed": overall >= cfg["offer_pass_score"] and not blockers, "blockers": blockers,
        "criteria": c, "economics": econ,
        "top_improvements": [{"criterion": x["criterion"], "issue": x["issues"][0], "fix": x["fixes"][0] if x["fixes"] else ""}
                             for x in weakest[:5]],
        "note": "Heuristic score of the offer definition. It is not a forecast of conversion or sales.",
    }


AWARENESS_LEAD = {
    "unaware": "Lead with a relatable situation/story; introduce the problem before the product.",
    "problem_aware": "Lead with the pain in the customer's words, then the mechanism that fixes it.",
    "solution_aware": "Lead with why this approach beats the alternatives they know.",
    "product_aware": "Lead with proof and specifics; remove remaining risk.",
    "most_aware": "Lead with the offer itself: price, what's included, how to start.",
}


def _f(offer: dict, key: str, placeholder: str) -> str:
    v = offer.get(key)
    if v in (None, "", []):
        return f"[{placeholder}]"
    return ", ".join(v) if isinstance(v, list) else str(v)


def generate_structures(offer: dict, awareness_levels: list[str] | None = None) -> dict:
    validate(offer, OFFER)
    price = offer.get("price")
    ptxt = f"{offer.get('currency', '')}{price}" if price is not None else "[SET PRICE]"
    base = {"customer": _f(offer, "target_customer", "TARGET CUSTOMER"), "outcome": _f(offer, "desired_outcome", "OUTCOME"),
            "deliverables": _f(offer, "deliverables", "DELIVERABLES")}
    proof_ok = any(p.get("verified") for p in offer.get("proof", []))
    structures = [
        {"structure": "core_offer", "for": "buyers ready to solve the problem now",
         "shape": f"{base['deliverables']} for {ptxt} ({offer.get('billing') or '[BILLING]'})"},
        {"structure": "entry_offer", "for": "cautious or price-sensitive buyers",
         "shape": "Smaller first step that delivers one quick win: [DEFINE SCOPE], priced below core: [SET PRICE]; credit toward core if true",
         "watch": "Must be profitable or a deliberate, measured acquisition cost."},
        {"structure": "pilot_or_trial", "for": "high-consideration or B2B buyers with perceived risk",
         "shape": "Time-boxed pilot with success criteria agreed up front: [CRITERIA]; [PILOT PRICE or FREE]",
         "watch": "Only promise criteria you control."},
        {"structure": "done_for_you_premium", "for": "time-poor buyers who value outcome over price",
         "shape": f"We implement {base['deliverables']} for you; premium price [SET PRICE]; capacity-limited only if genuinely limited"},
        {"structure": "subscription", "for": "ongoing problems / recurring need",
         "shape": "Monthly plan covering [RECURRING DELIVERABLE]; cancel terms: [TERMS]",
         "watch": "Retention data decides viability; model churn before committing."},
        {"structure": "bundle", "for": "buyers comparing several vendors",
         "shape": f"Core + complementary items buyers already purchase separately: [ITEMS]; bonuses only if real: {_f(offer, 'bonuses', 'NONE')}"},
    ]
    levels = awareness_levels or AWARENESS
    angles = [{"awareness": a, "lead_with": AWARENESS_LEAD[a],
               "headline_skeleton": {
                   "unaware": f"[RELATABLE SITUATION] -> {base['outcome']}",
                   "problem_aware": f"Tired of [PAIN IN CUSTOMER WORDS]? {base['outcome']}",
                   "solution_aware": f"{base['outcome']} without [DOWNSIDE OF ALTERNATIVE]",
                   "product_aware": ("[VERIFIED PROOF POINT] - " if not proof_ok else "[USE A VERIFIED PROOF ITEM] - ") + base["outcome"],
                   "most_aware": f"{base['deliverables']} for {ptxt}. Start [HOW]",
               }[a]} for a in levels if a in AWARENESS_LEAD]
    return {"structures": structures, "awareness_angles": angles,
            "rules": ["Fill every [PLACEHOLDER] with real facts or drop that element",
                      "No invented guarantees, testimonials, results or scarcity",
                      "Score each filled structure with score_offer() before use"]}


def to_record(offer: dict, score: dict | None = None, product: str | None = None) -> dict:
    return {"kind": "offer", "title": f"Offer: {offer['name']}"[:300], "product": product,
            "audience": offer.get("target_customer"), "basis": "inferred",
            "confidence": "medium" if score and score["passed"] else "low", "tags": ["offer"],
            "natural_key": f"offer|{product or ''}|{offer['name']}",
            "data": {"offer": offer, "score": score}}
