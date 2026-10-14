"""Ad creative and campaign engine.

- ANGLES: 10 genuinely different creative strategies (not rewrites).
- PLATFORMS: configurable channel profiles (formats, objectives, notes). No
  account access or live integration is assumed or attempted.
- generate_concepts(): one concept per angle, filled from real inputs; each has a
  hook skeleton, message, proof requirement, CTA, funnel stage, hypothesis,
  measurement plan, failure points and a readiness flag (ready / needs_proof / needs_input).
  Diversity is measured; near-duplicates are flagged.
- campaign_plan(): objective -> metric mapping, budget arithmetic from YOUR
  assumptions (labelled), measurement plan and risks.
- VariantRegistry: store concepts, variants (with QC result), and real results;
  compare variants with proper statistics. Never launches or spends anything.
"""

from __future__ import annotations

from . import metrics as M
from . import qc as QC
from . import text as T
from .config import load_config
from .experiments import analyze as analyze_arms
from .schemas import CAMPAIGN_RESULT, validate
from .store import KnowledgeStore

ANGLES: dict[str, dict] = {
    "problem_led": {"hook": "\"{pain}\" Sound familiar?", "structure": "pain -> consequence -> solution -> CTA",
                    "needs": ["pain"], "proof": "optional", "stage": "discovery", "awareness": ["problem_aware"],
                    "failure": "Pain not felt strongly by this audience; reads as negative."},
    "product_demo": {"hook": "Watch {product} {job} in {time}", "structure": "task -> screen/hands-on demo -> result -> CTA",
                     "needs": ["product", "job"], "proof": "the demo itself (must be real footage)", "stage": "discovery",
                     "awareness": ["solution_aware", "product_aware"], "failure": "Demo too slow; value not visible in first 3 seconds."},
    "customer_proof": {"hook": "\"{verified_quote}\"", "structure": "real customer result -> how -> CTA",
                       "needs": ["verified_quote"], "proof": "verified, permissioned testimonial/case", "stage": "consideration",
                       "awareness": ["product_aware"], "failure": "Proof not relatable to the viewer's situation."},
    "objection_handling": {"hook": "\"{objection}\"? Here's the honest answer.", "structure": "objection -> truthful answer -> evidence -> CTA",
                           "needs": ["objection"], "proof": "evidence that answers the objection", "stage": "consideration",
                           "awareness": ["solution_aware", "product_aware"], "failure": "Raises an objection the viewer didn't have."},
    "comparison": {"hook": "{alternative} vs {product}: {difference}", "structure": "status quo -> concrete difference -> who it's for -> CTA",
                   "needs": ["alternative", "difference"], "proof": "verifiable comparison facts", "stage": "consideration",
                   "awareness": ["solution_aware"], "failure": "Unfair/unverifiable comparison: legal and policy risk."},
    "founder_story": {"hook": "Why I built {product}", "structure": "founder's real problem -> insight -> product -> CTA",
                      "needs": ["product"], "proof": "authentic founder footage", "stage": "discovery",
                      "awareness": ["unaware", "problem_aware"], "failure": "About the founder, not the viewer."},
    "outcome_visualization": {"hook": "Imagine {outcome}", "structure": "desired end state -> how it happens -> CTA",
                              "needs": ["outcome"], "proof": "realistic outcome only", "stage": "discovery",
                              "awareness": ["problem_aware", "solution_aware"], "failure": "Outcome feels exaggerated or generic."},
    "educational": {"hook": "{n} mistakes {audience} make with {topic}", "structure": "useful lesson -> product as next step -> soft CTA",
                    "needs": ["topic"], "proof": "accurate advice", "stage": "discovery", "awareness": ["unaware", "problem_aware"],
                    "failure": "Educates without driving action; attracts non-buyers."},
    "unexpected_use_case": {"hook": "We didn't expect {audience} to use {product} for {use_case}", "structure": "surprising real use -> why it works -> CTA",
                            "needs": ["use_case"], "proof": "a real observed use case", "stage": "discovery",
                            "awareness": ["unaware", "solution_aware"], "failure": "Novelty without relevance to the core buyer."},
    "offer_led": {"hook": "{offer_terms}", "structure": "offer -> what's included -> risk reversal -> CTA",
                  "needs": ["offer_terms"], "proof": "real, current offer terms", "stage": "conversion",
                  "awareness": ["product_aware", "most_aware"], "failure": "Discount-trained buyers; margin erosion."},
}

PLATFORMS: dict[str, dict] = {
    "meta": {"formats": ["image", "video (4:5/9:16)", "carousel"], "objectives": ["awareness", "traffic", "leads", "sales", "app_installs"],
             "copy_fields": ["meta_primary_text", "meta_headline"], "notes": "Personal-attribute and health/finance claim rules apply."},
    "google_search": {"formats": ["responsive search ad"], "objectives": ["leads", "sales", "traffic"],
                      "copy_fields": ["google_rsa_headline", "google_rsa_description"], "notes": "Intent-driven: match the query, lead with the offer."},
    "tiktok": {"formats": ["9:16 video", "spark ads"], "objectives": ["awareness", "traffic", "leads", "sales", "app_installs"],
               "copy_fields": ["tiktok_ad_text"], "notes": "Native, creator-style video; hook in first 1-2 seconds."},
    "youtube": {"formats": ["skippable in-stream", "shorts"], "objectives": ["awareness", "consideration", "sales"],
                "copy_fields": ["youtube_script_15s", "youtube_script_30s"], "notes": "Value before the skip button (5s)."},
    "linkedin": {"formats": ["single image", "document", "video"], "objectives": ["awareness", "leads"],
                 "copy_fields": ["linkedin_post"], "notes": "B2B; role/company targeting; higher CPCs typical."},
}

OBJECTIVE_METRICS = {
    "awareness": ("cpm / reach", ["frequency", "video_view_rate"]),
    "traffic": ("cost per landing page view", ["bounce_rate", "ctr"]),
    "leads": ("cost per qualified lead", ["lead_to_customer", "cpl"]),
    "sales": ("cpa and contribution margin per order", ["roas_vs_breakeven", "refund_rate"]),
    "app_installs": ("cost per activated user", ["install_to_activation", "day7_retention"]),
    "consideration": ("cost per engaged view", ["ctr", "landing_conversion"]),
}


class _Safe(dict):
    def __missing__(self, key):
        return "{" + key.upper() + "}"


def _inputs(brief: dict) -> dict:
    offer = brief.get("offer") or {}
    proofs = [p for p in brief.get("proof", []) if p.get("verified")]
    return {
        "product": offer.get("name") or brief.get("product"),
        "pain": (brief.get("pains") or [None])[0], "outcome": (brief.get("outcomes") or [offer.get("desired_outcome")])[0],
        "objection": (brief.get("objections") or [None])[0], "alternative": (offer.get("alternatives") or [None])[0],
        "difference": offer.get("differentiation"), "job": brief.get("job"), "time": brief.get("demo_time"),
        "verified_quote": proofs[0]["text"] if proofs else None, "audience": brief.get("audience") or offer.get("target_customer"),
        "topic": brief.get("topic"), "use_case": brief.get("use_case"), "n": brief.get("n_mistakes", 3),
        "offer_terms": brief.get("offer_terms"), "cta": brief.get("cta"),
    }


def generate_concepts(brief: dict, angles: list[str] | None = None, platforms: list[str] | None = None,
                      config: dict | None = None) -> dict:
    """brief: {offer, pains, outcomes, objections, proof[{text, verified}], audience, job, demo_time,
    topic, use_case, offer_terms, cta, objective, landing_text}"""
    cfg = load_config(config)
    vals = _inputs(brief)
    platforms = platforms or brief.get("platforms") or ["meta"]
    objective = brief.get("objective", "leads")
    concepts = []
    for name in angles or list(ANGLES):
        a = ANGLES[name]
        missing = [k for k in a["needs"] if not vals.get(k)]
        hook = a["hook"].format_map(_Safe({k: v for k, v in vals.items() if v}))
        readiness = "needs_input" if missing else ("needs_proof" if name in ("customer_proof",) and not vals["verified_quote"] else "ready")
        message = {
            "problem_led": f"{vals['pain'] or '[PAIN]'} -> {vals['outcome'] or '[OUTCOME]'} with {vals['product'] or '[PRODUCT]'}",
            "product_demo": f"Show {vals['product'] or '[PRODUCT]'} doing {vals['job'] or '[JOB]'} end-to-end",
            "customer_proof": f"Real customer result: {vals['verified_quote'] or '[VERIFIED PROOF NEEDED]'}",
            "objection_handling": f"Answer '{vals['objection'] or '[OBJECTION]'}' truthfully with evidence",
            "comparison": f"{vals['difference'] or '[VERIFIABLE DIFFERENCE]'} vs {vals['alternative'] or '[ALTERNATIVE]'}",
            "founder_story": "Founder explains the real problem that led to the product",
            "outcome_visualization": f"Picture: {vals['outcome'] or '[OUTCOME]'}",
            "educational": f"Teach one useful thing about {vals['topic'] or '[TOPIC]'}; product as next step",
            "unexpected_use_case": f"Real surprising use: {vals['use_case'] or '[USE CASE]'}",
            "offer_led": f"{vals['offer_terms'] or '[OFFER TERMS]'}",
        }[name]
        primary, guards = OBJECTIVE_METRICS.get(objective, ("cpa", []))
        c = {
            "concept_id": f"{name}", "angle": name, "hook": hook, "structure": a["structure"], "main_message": message,
            "proof_required": a["proof"], "offer": (brief.get("offer") or {}).get("name"),
            "cta": vals["cta"] or "[ONE CTA]", "funnel_stage": a["stage"], "awareness_fit": a["awareness"],
            "platform_formats": {p: PLATFORMS[p]["formats"] for p in platforms if p in PLATFORMS},
            "hypothesis": (f"For {vals['audience'] or '[AUDIENCE]'}, a {name.replace('_', ' ')} creative will beat the current best on "
                           f"{primary} because {(brief.get('insight') or '[CUSTOMER INSIGHT / EVIDENCE ID]')}"),
            "measurement": {"primary_metric": primary, "guardrails": guards,
                            "decision_rule": "Compare against control with experiments.analyze(); no winner below minimum sample."},
            "landing_match": "Landing hero must repeat this hook's promise and offer." if not brief.get("landing_text") else None,
            "likely_failure_points": [a["failure"]] + ([f"missing inputs: {missing}"] if missing else []),
            "missing_inputs": missing, "readiness": readiness,
        }
        if brief.get("landing_text"):
            mm = QC.evaluate(f"{hook}. {message}", {"kind": "copy", "landing_text": brief["landing_text"], "require_cta": False})
            c["landing_match"] = "ok" if not any(f["code"] == "message_mismatch" for f in mm["findings"]) else "mismatch: align landing hero"
        concepts.append(c)
    texts = [f"{c['hook']} {c['main_message']} {c['structure']}" for c in concepts]
    sims = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            s = T.similarity(texts[i], texts[j])
            if s >= cfg["concept_similarity_threshold"]:
                sims.append({"a": concepts[i]["angle"], "b": concepts[j]["angle"], "similarity": round(s, 2)})
    return {"objective": objective, "platforms": platforms, "concepts": concepts, "near_duplicates": sims,
            "ready": [c["angle"] for c in concepts if c["readiness"] == "ready"],
            "note": "Concepts are hypotheses. Hooks with {PLACEHOLDERS} need real inputs; never fill proof with invented material."}


def campaign_plan(brief: dict, budget: dict | None = None, config: dict | None = None) -> dict:
    """budget (all YOUR assumptions): {"daily": 50, "days": 14, "assumed_cpc": 1.5, "assumed_cvr": 0.03,
    "gross_margin": 0.6, "aov": 120}. Projections are arithmetic on assumptions, not forecasts."""
    gen = generate_concepts(brief, config=config)
    plan = {
        "objective": gen["objective"], "audience": brief.get("audience"), "awareness": brief.get("awareness"),
        "concepts_to_test": [c["angle"] for c in gen["concepts"] if c["readiness"] == "ready"][:4],
        "concepts_blocked": {c["angle"]: c["missing_inputs"] or c["readiness"] for c in gen["concepts"] if c["readiness"] != "ready"},
        "funnel": {"discovery": [c["angle"] for c in gen["concepts"] if c["funnel_stage"] == "discovery"],
                   "consideration": [c["angle"] for c in gen["concepts"] if c["funnel_stage"] == "consideration"],
                   "conversion": [c["angle"] for c in gen["concepts"] if c["funnel_stage"] == "conversion"]},
        "measurement_plan": {"primary_metric": OBJECTIVE_METRICS.get(gen["objective"], ("cpa", []))[0],
                             "guardrails": OBJECTIVE_METRICS.get(gen["objective"], ("cpa", []))[1],
                             "tracking_events": ["page_view", "lead_submitted / purchase", "utm_source/medium/campaign/content"],
                             "decision_rule": "Fixed budget per concept; analyze with experiments.analyze() after min sample"},
        "approval_required": ["launching any campaign", "spending budget", "publishing creative"],
        "risks": sorted({c["likely_failure_points"][0] for c in gen["concepts"]}),
    }
    if budget:
        b = dict(budget)
        total = (b.get("daily") or 0) * (b.get("days") or 0)
        proj = {"total_budget": total, "basis": "assumption"}
        if b.get("assumed_cpc"):
            clicks = total / b["assumed_cpc"]
            proj["clicks"] = round(clicks)
            if b.get("assumed_cvr"):
                conv = clicks * b["assumed_cvr"]
                proj["conversions"] = round(conv, 1)
                proj["cpa"] = round(total / conv, 2) if conv else None
                if b.get("aov") and b.get("gross_margin"):
                    proj["revenue"] = round(conv * b["aov"], 2)
                    proj["gross_profit_minus_spend"] = round(conv * b["aov"] * b["gross_margin"] - total, 2)
                    proj["breakeven_cpa"] = round(b["aov"] * b["gross_margin"], 2)
            per_concept = total / max(1, len(plan["concepts_to_test"]))
            proj["budget_per_concept"] = round(per_concept, 2)
            if b.get("assumed_cvr"):
                exp_conv = per_concept / b["assumed_cpc"] * b["assumed_cvr"]
                proj["expected_conversions_per_concept"] = round(exp_conv, 1)
                if exp_conv < load_config(config)["min_conversions_per_arm"]:
                    proj["warning"] = (f"~{exp_conv:.0f} conversions per concept is below the minimum for a reliable comparison; "
                                       "test fewer concepts, raise budget, or optimise on an earlier funnel metric (CTR/CPC) and label it directional.")
        plan["budget_projection"] = proj
    plan["concepts"] = gen["concepts"]
    return plan


class VariantRegistry:
    """Track concepts -> variants -> results in the KnowledgeStore."""

    def __init__(self, store: KnowledgeStore, config: dict | None = None):
        self.store, self.cfg = store, load_config(config)

    def register_concept(self, concept: dict, product: str | None = None, audience: str | None = None) -> str:
        rid, _ = self.store.add({
            "kind": "ad_concept", "title": f"{concept['angle']}: {concept['hook']}"[:300], "product": product,
            "audience": audience, "basis": "hypothesis", "confidence": "low", "tags": ["ad", concept["angle"]],
            "natural_key": f"concept|{product or ''}|{audience or ''}|{concept['angle']}|{concept['hook']}",
            "data": concept}, on_conflict="version")
        return rid

    def add_variant(self, concept_id: str, copy_text: str, platform: str, audience: str | None = None,
                    hypothesis: str | None = None, version: str = "v1", qc_context: dict | None = None) -> dict:
        concept = self.store.get(concept_id)
        if not concept or concept["kind"] != "ad_concept":
            raise KeyError(f"unknown concept {concept_id}")
        import hashlib
        nkey = f"variant|{concept_id}|{platform}|{version}|{hashlib.sha1(copy_text.encode()).hexdigest()[:12]}"
        existing = self.store.find(kind="ad_variant", text=concept_id, include_archived=True)
        for v in existing:
            if v.get("natural_key") == nkey:
                return {"variant_id": v["id"], "action": "existing", "qc_decision": v["data"]["qc"]["decision"],
                        "qc_findings": v["data"]["qc"]["findings"]}
        others = [v["data"]["copy"] for v in existing if v["data"]["copy"] != copy_text]
        ctx = {"kind": "ad", "platform": platform, "other_concepts": others, **(qc_context or {})}
        qc = QC.evaluate(copy_text, ctx, self.cfg)
        rid, action = self.store.add({
            "kind": "ad_variant", "title": f"{concept['data']['angle']} {version} [{platform}]: {copy_text[:60]}"[:300],
            "product": concept.get("product"), "audience": audience or concept.get("audience"),
            "basis": "hypothesis", "confidence": "low", "tags": ["ad", platform, concept["data"]["angle"]],
            "sources": [concept_id], "status": "draft" if qc["decision"] != "reject" else "rejected_by_qc", "natural_key": nkey,
            "data": {"concept_id": concept_id, "copy": copy_text, "platform": platform, "version": version,
                     "hypothesis": hypothesis or concept["data"].get("hypothesis"), "qc": qc}})
        return {"variant_id": rid, "action": action, "qc_decision": qc["decision"], "qc_findings": qc["findings"]}

    def record_result(self, variant_id: str, result: dict) -> str:
        """result follows schemas.CAMPAIGN_RESULT; metrics must come from real platform/analytics exports."""
        v = self.store.get(variant_id)
        if not v or v["kind"] != "ad_variant":
            raise KeyError(f"unknown variant {variant_id}")
        result = {**result, "variant_id": variant_id}
        validate(result, CAMPAIGN_RESULT)
        rid, _ = self.store.add({
            "kind": "campaign_result", "title": result["title"], "product": v.get("product"), "audience": v.get("audience"),
            "basis": "measured", "confidence": "medium", "tags": ["result", result.get("platform", "")],
            "sources": [variant_id], "data": {**result, "summary": M.campaign_summary(result["metrics"])}})
        return rid

    def results_for(self, variant_id: str) -> list[dict]:
        return [r for r in self.store.find(kind="campaign_result") if variant_id in r["sources"]]

    def compare(self, variant_ids: list[str], conversion_metric: str = "conversions", exposure_metric: str = "clicks",
                gross_margin_rate: float | None = None) -> dict:
        rows, arms = [], {}
        for vid in variant_ids:
            agg: dict = {}
            for r in self.results_for(vid):
                for k, val in r["data"]["metrics"].items():
                    if isinstance(val, (int, float)):
                        agg[k] = agg.get(k, 0) + val
            summ = M.campaign_summary(agg, gross_margin_rate) if agg else {}
            rows.append({"variant_id": vid, "totals": agg,
                         "ctr": summ.get("ctr", {}).get("value"), "cpc": summ.get("cpc", {}).get("value"),
                         "cpa": summ.get("cpa", {}).get("value"), "roas": summ.get("roas", {}).get("value"),
                         "profitable_on_first_purchase": summ.get("profitable_on_first_purchase")})
            if agg.get(exposure_metric) and agg.get(conversion_metric) is not None:
                arms[vid] = {"n": int(agg[exposure_metric]), "conversions": int(agg[conversion_metric])}
        stats = None
        if len(arms) >= 2:
            control = variant_ids[0] if variant_ids[0] in arms else next(iter(arms))
            stats = analyze_arms(arms, control, config=self.cfg)
        return {"rows": rows, "statistics": stats,
                "note": "Winner declared only via statistics.decisions; ROAS is revenue-based, check profitability separately."}
