"""Reusable, brand-neutral marketing components.

- render_landing(): semantic, mobile-first, accessible landing page HTML from a
  config (hero, problem, how-it-works, proof, pricing, FAQ, lead form, final CTA).
  Proof items are rendered only if marked verified; theming via CSS variables.
- React version: templates/LandingSections.jsx (+ templates/landing.css).
- Text templates: emails, ad brief, sales script, campaign plan, onboarding flow,
  upgrade prompts; render_template() reports missing placeholders instead of guessing.
- ANALYTICS_EVENTS: a standard event schema + validate_event().
"""

from __future__ import annotations

import html
import string

E = html.escape

BASE_CSS = """:root{--bg:#fff;--fg:#111;--muted:#555;--accent:#2557d6;--accent-fg:#fff;--radius:10px;--max:1080px;
--font:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#f2f2f2;--muted:#a8a8a8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 var(--font)}
section{padding:56px 16px}.wrap{max-width:var(--max);margin:0 auto}h1{font-size:clamp(28px,5vw,48px);line-height:1.15;margin:0 0 12px}
h2{font-size:clamp(22px,3.5vw,32px);margin:0 0 16px}.sub{color:var(--muted);font-size:18px;max-width:640px}
.cta{display:inline-block;background:var(--accent);color:var(--accent-fg);padding:14px 22px;border-radius:var(--radius);
text-decoration:none;font-weight:600;border:0;font-size:16px;cursor:pointer}.cta:focus-visible{outline:3px solid var(--fg)}
.grid{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}.card{border:1px solid #8883;border-radius:var(--radius);padding:20px}
.plan.featured{border:2px solid var(--accent)}.price{font-size:32px;font-weight:700}.note{color:var(--muted);font-size:14px}
form{display:grid;gap:12px;max-width:420px}input{padding:12px;border-radius:8px;border:1px solid #8886;font-size:16px}
details{border-bottom:1px solid #8883;padding:12px 0}summary{cursor:pointer;font-weight:600}"""


def _section(sid: str, inner: str) -> str:
    return f'<section id="{E(sid)}"><div class="wrap">{inner}</div></section>'


def render_landing(cfg: dict) -> dict:
    """cfg: {
      "lang": "en", "title", "meta_description",
      "hero": {"headline", "subheadline", "cta_text", "cta_href", "secondary": str?},
      "problem": {"heading", "points": [str]},
      "how_it_works": {"heading", "steps": [{"title", "text"}]},
      "proof": {"heading", "items": [{"quote"|"stat", "attribution", "verified": bool, "source_ref"}]},
      "pricing": {"heading", "plans": [{"name", "price", "period", "features": [], "cta_text", "cta_href", "featured": bool}], "note"},
      "faq": {"heading", "items": [{"q", "a"}]},
      "lead_form": {"heading", "fields": [{"name", "label", "type", "required"}], "submit_text", "action", "privacy_note"},
      "final_cta": {"heading", "cta_text", "cta_href"},
      "analytics": true  -> adds data-event attributes for ANALYTICS_EVENTS}"""
    warnings = []
    ev = (lambda name: f' data-event="{name}"') if cfg.get("analytics", True) else (lambda name: "")
    parts = []
    h = cfg.get("hero") or {}
    if not h.get("headline"):
        warnings.append("hero.headline missing")
    hero = f'<h1>{E(h.get("headline", "[HEADLINE]"))}</h1>'
    if h.get("subheadline"):
        hero += f'<p class="sub">{E(h["subheadline"])}</p>'
    hero += f'<p><a class="cta" href="{E(h.get("cta_href", "#signup"))}"{ev("cta_click")} data-cta="hero">{E(h.get("cta_text", "[CTA]"))}</a></p>'
    if h.get("secondary"):
        hero += f'<p class="note">{E(h["secondary"])}</p>'
    parts.append(_section("hero", hero))

    if cfg.get("problem"):
        p = cfg["problem"]
        parts.append(_section("problem", f'<h2>{E(p.get("heading", ""))}</h2><ul>' +
                              "".join(f"<li>{E(x)}</li>" for x in p.get("points", [])) + "</ul>"))
    if cfg.get("how_it_works"):
        w = cfg["how_it_works"]
        parts.append(_section("how-it-works", f'<h2>{E(w.get("heading", "How it works"))}</h2><ol class="grid">' +
                              "".join(f'<li class="card"><strong>{E(s["title"])}</strong><p>{E(s.get("text", ""))}</p></li>'
                                      for s in w.get("steps", [])) + "</ol>"))
    if cfg.get("proof"):
        pr = cfg["proof"]
        items = [i for i in pr.get("items", []) if i.get("verified")]
        dropped = len(pr.get("items", [])) - len(items)
        if dropped:
            warnings.append(f"{dropped} unverified proof item(s) omitted")
        if items:
            cards = ""
            for i in items:
                body = f'<blockquote>{E(i["quote"])}</blockquote>' if i.get("quote") else f'<p class="price">{E(i.get("stat", ""))}</p>'
                cards += f'<figure class="card">{body}<figcaption class="note">{E(i.get("attribution", ""))}</figcaption></figure>'
            parts.append(_section("proof", f'<h2>{E(pr.get("heading", "What customers say"))}</h2><div class="grid">{cards}</div>'))
    if cfg.get("pricing"):
        pc = cfg["pricing"]
        cards = ""
        for pl in pc.get("plans", []):
            feat = "".join(f"<li>{E(f)}</li>" for f in pl.get("features", []))
            badge = '<p class="note">Recommended</p>' if pl.get("featured") else ""
            cards += (f'<div class="card plan{" featured" if pl.get("featured") else ""}">{badge}<h3>{E(pl["name"])}</h3>'
                      f'<p class="price">{E(str(pl.get("price", "")))}<span class="note">{E(pl.get("period", ""))}</span></p><ul>{feat}</ul>'
                      f'<a class="cta" href="{E(pl.get("cta_href", "#signup"))}"{ev("cta_click")} data-cta="pricing-{E(pl["name"])}">'
                      f'{E(pl.get("cta_text", "Choose"))}</a></div>')
        note = f'<p class="note">{E(pc["note"])}</p>' if pc.get("note") else ""
        parts.append(_section("pricing", f'<h2>{E(pc.get("heading", "Pricing"))}</h2><div class="grid">{cards}</div>{note}'))
        if len(pc.get("plans", [])) >= 3 and not any(pl.get("featured") for pl in pc["plans"]):
            warnings.append("3+ plans without a featured/recommended plan")
    if cfg.get("faq"):
        fq = cfg["faq"]
        parts.append(_section("faq", f'<h2>{E(fq.get("heading", "Questions"))}</h2>' +
                              "".join(f"<details><summary>{E(i['q'])}</summary><p>{E(i['a'])}</p></details>" for i in fq.get("items", []))))
    if cfg.get("lead_form"):
        lf = cfg["lead_form"]
        fields = lf.get("fields") or [{"name": "email", "label": "Email", "type": "email", "required": True}]
        if len(fields) > 5:
            warnings.append(f"lead form has {len(fields)} fields; consider fewer")
        inputs = "".join(
            f'<label for="f-{E(f["name"])}">{E(f.get("label", f["name"]))}</label>'
            f'<input id="f-{E(f["name"])}" name="{E(f["name"])}" type="{E(f.get("type", "text"))}"'
            f'{" required" if f.get("required") else ""} autocomplete="{E(f.get("autocomplete", f["name"]))}">' for f in fields)
        privacy = f'<p class="note">{E(lf.get("privacy_note", "We only use your details to respond. No spam."))}</p>'
        parts.append(_section("signup", f'<h2>{E(lf.get("heading", "Get started"))}</h2>'
                              f'<form method="post" action="{E(lf.get("action", "#"))}"{ev("lead_submitted")}>{inputs}'
                              f'<button class="cta" type="submit">{E(lf.get("submit_text", "[ACTION + VALUE]"))}</button>{privacy}</form>'))
    if cfg.get("final_cta"):
        fc = cfg["final_cta"]
        parts.append(_section("final-cta", f'<h2>{E(fc.get("heading", ""))}</h2><a class="cta" href="{E(fc.get("cta_href", "#signup"))}"'
                              f'{ev("cta_click")} data-cta="final">{E(fc.get("cta_text", "[CTA]"))}</a>'))
    page = (f'<!doctype html><html lang="{E(cfg.get("lang", "en"))}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(cfg.get("title", h.get("headline", "")))}</title>'
            f'<meta name="description" content="{E(cfg.get("meta_description", h.get("subheadline", "")))}"><style>{BASE_CSS}</style></head>'
            f'<body><main>{"".join(parts)}</main></body></html>')
    return {"html": page, "warnings": warnings}


# ---------------------------------------------------------------- text templates
TEMPLATES: dict[str, str] = {
    "email_welcome": "Subject: {product}: your first step\n\nHi {first_name},\n\nThanks for signing up. The fastest way to {first_value} is:\n1. {step_1}\n2. {step_2}\n\n{cta_text}: {cta_url}\n\nQuestions? Just reply.\n{sender}",
    "email_onboarding_nudge": "Subject: {first_name}, you're one step from {first_value}\n\nYou started {started_action} but haven't {activation_action} yet. Most people get stuck at {common_blocker}; here's how to get past it: {help}.\n\n{cta_text}: {cta_url}\n{sender}",
    "email_abandoned_cart": "Subject: Still thinking about {item}?\n\nYou left {item} in your cart. If something held you back ({top_objection}?), {objection_answer}.\n\n{cta_text}: {cta_url}\n\n{real_terms_only}\n{sender}",
    "email_win_back": "Subject: {first_name}, a lot has changed since you left\n\nYou left because {cancellation_reason}. Since then we've {relevant_change}.\n\nIf that fixes it for you: {cta_text} {cta_url}\nIf not, no hard feelings.\n{sender}",
    "email_demo_follow_up": "Subject: {company}: next steps from our call\n\nHi {first_name},\n\nYou said the main issue is {their_problem_in_their_words}, costing about {their_estimate}. We agreed {agreed_next_step}.\n\nYou asked about {their_question}: {answer}.\n\nDoes {proposed_time} still work?\n{sender}",
    "cold_outreach": "Subject: {specific_observation}\n\nHi {first_name}, {why_them_specific_and_true}. We help {segment} {outcome} (e.g. {verified_proof}). Worth a 15-minute call to see if it fits? If not, I won't follow up more than once.\n{sender}",
    "upgrade_prompt": "{trigger_context}: You've {usage_fact}. {plan} lets you {benefit}. [{cta_text}]  [Not now]",
    "ad_brief": "OBJECTIVE: {objective}\nAUDIENCE: {audience} (awareness: {awareness})\nINSIGHT (evidence {evidence_id}): {insight}\nANGLE: {angle}\nHOOK: {hook}\nMESSAGE: {message}\nPROOF (verified only): {proof}\nOFFER: {offer}\nCTA: {cta}\nLANDING PAGE: {landing_url} (must echo the hook)\nFORMATS: {formats}\nPRIMARY METRIC: {primary_metric}  GUARDRAILS: {guardrails}\nHYPOTHESIS: {hypothesis}\nCOMPLIANCE NOTES: {compliance_notes}",
    "sales_script": "OPEN: {opener} (set agenda, ask permission)\nSITUATION: {situation_q}\nPROBLEM: {problem_q}\nIMPACT: {impact_q}\nOUTCOME: {outcome_q}\nDECISION: {decision_q}\nFIT CHECK: does {product} solve {their_problem}? If not, say so.\nPRESENT: only the 2-3 capabilities tied to their problem: {capabilities}\nOBJECTIONS: clarify first; use sales.handle_objection()\nNEXT STEP: {next_step} with date",
    "campaign_plan": "CAMPAIGN: {name}\nGOAL: {goal} | PRIMARY METRIC: {primary_metric} | GUARDRAILS: {guardrails}\nAUDIENCE: {audience}\nCONCEPTS: {concepts}\nBUDGET (assumption): {budget} over {days} days\nTRACKING: {tracking_events}\nDECISION RULE: {decision_rule}\nAPPROVALS NEEDED: launch, spend, publish",
}


def placeholders(template: str) -> list[str]:
    return sorted({f for _, f, _, _ in string.Formatter().parse(template) if f})


def render_template(name_or_text: str, values: dict, strict: bool = False) -> dict:
    tpl = TEMPLATES.get(name_or_text, name_or_text)
    needed = placeholders(tpl)
    missing = [p for p in needed if values.get(p) in (None, "")]
    if strict and missing:
        raise KeyError(f"missing values: {missing}")
    filled = tpl
    for p in needed:
        v = values.get(p)
        filled = filled.replace("{" + p + "}", str(v) if v not in (None, "") else f"[{p.upper()}]")
    return {"text": filled, "missing": missing}


ONBOARDING_FLOW_TEMPLATE = {
    "principle": "Shortest path to first value; ask for everything else later.",
    "steps": [
        {"name": "signup", "fields": ["email", "password or SSO"], "delivers_value": False},
        {"name": "one key question", "purpose": "personalise first screen (optional)", "optional": True},
        {"name": "first win", "delivers_value": True, "examples": ["template applied", "sample data", "first result generated"]},
        {"name": "celebrate + next step", "delivers_value": True},
        {"name": "invite / integrate", "optional": True, "timing": "after first win"},
    ],
    "measure": ["signup_completed", "activation event", "time_to_activation", "day7_retention"],
}

# ---------------------------------------------------------------- analytics
ANALYTICS_EVENTS: dict[str, dict] = {
    "page_view": {"required": ["page", "utm_source"], "optional": ["utm_medium", "utm_campaign", "utm_content", "referrer", "experiment_id", "variant"]},
    "cta_click": {"required": ["page", "cta"], "optional": ["variant", "experiment_id"]},
    "lead_submitted": {"required": ["form", "page"], "optional": ["fields_count", "variant"]},
    "signup_started": {"required": ["method"], "optional": ["variant"]},
    "signup_completed": {"required": ["method"], "optional": ["variant", "seconds_to_complete"]},
    "activation": {"required": ["activation_event"], "optional": ["seconds_since_signup"]},
    "trial_started": {"required": ["plan"], "optional": []},
    "purchase": {"required": ["order_id", "value", "currency"], "optional": ["items", "coupon", "variant", "gross_margin"]},
    "subscription_cancelled": {"required": ["plan", "reason"], "optional": ["tenure_days"]},
    "upgrade_prompt_shown": {"required": ["trigger", "plan"], "optional": ["variant"]},
    "upgrade_prompt_clicked": {"required": ["trigger", "plan"], "optional": ["variant"]},
    "experiment_exposure": {"required": ["experiment_id", "variant"], "optional": []},
    "refund": {"required": ["order_id", "value"], "optional": ["reason"]},
}


def validate_event(event: dict) -> list[str]:
    name = event.get("event")
    if name not in ANALYTICS_EVENTS:
        return [f"unknown event {name!r}; known: {sorted(ANALYTICS_EVENTS)}"]
    spec = ANALYTICS_EVENTS[name]
    props = event.get("properties", {})
    errs = [f"{name}: missing property {p}" for p in spec["required"] if p not in props]
    extra = [p for p in props if p not in spec["required"] + spec["optional"]]
    if extra:
        errs.append(f"{name}: undocumented properties {extra} (add to schema or remove)")
    if name == "purchase" and "value" in props and not isinstance(props["value"], (int, float)):
        errs.append("purchase.value must be a number")
    return errs


def tracking_plan(funnel_stages: list[str]) -> list[dict]:
    mapping = {"discovery": "page_view", "landing": "cta_click", "lead": "lead_submitted", "signup": "signup_completed",
               "activation": "activation", "trial": "trial_started", "purchase": "purchase", "retention": "subscription_cancelled"}
    return [{"stage": s, "event": mapping.get(s, "custom"), "properties": ANALYTICS_EVENTS.get(mapping.get(s, ""), {})} for s in funnel_stages]
