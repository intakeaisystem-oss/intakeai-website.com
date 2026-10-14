"""Funnel and conversion optimisation engine.

- diagnose_funnel(): stage conversion/drop-off, data sufficiency, message
  consistency between stages, offer/traffic match, trust-before-ask, activation
  speed, follow-up vs real objections.
- audit_landing_html(): code-aware audit of an HTML page (also works on
  JSX/TSX/Vue/Svelte markup via a best-effort conversion). Checks hero,
  headline, offer clarity, CTAs, proof/trust, forms, mobile, pricing,
  checkout friction, distractions and basic accessibility, with line numbers.
- audit_onboarding(): signup -> activation -> upgrade flow audit.

Every recommendation carries a conversion *hypothesis* and a way to test it.
No recommendation claims a specific % improvement.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from . import metrics as M
from . import text as T
from .qc import CTA_VERBS, PROOF_SIGNALS
from .schemas import FUNNEL_INPUT, validate

HIGH_COMMITMENT_CTAS = ["buy", "purchase", "subscribe", "order", "pay", "checkout"]
LOW_COMMITMENT_CTAS = ["learn", "see", "watch", "read", "explore", "download", "try", "get the guide", "free"]


def _rec(area, severity, finding, recommendation, hypothesis, evidence=None, line=None, test="A/B test or usability test"):
    return {"area": area, "severity": severity, "finding": finding, "recommendation": recommendation,
            "hypothesis": hypothesis, "how_to_test": test, "evidence": evidence or [], "line": line}


# ---------------------------------------------------------------- funnel diagnostics
def diagnose_funnel(inp: dict, objections: list[str] | None = None, follow_ups: list[str] | None = None,
                    min_stage_n: int = 100) -> dict:
    validate(inp, FUNNEL_INPUT)
    stages = inp["stages"]
    f = M.funnel([{"name": s["name"], "count": s["count"]} for s in stages])
    recs = []
    if not f["ok"] and not f["stages"]:
        return {"funnel": f, "recommendations": [], "error": f["error"]}
    if f["error"]:
        recs.append(_rec("data", "high", f["error"], "Fix tracking before optimising anything.",
                         "Bad data leads to optimising the wrong stage.", test="Audit analytics events end-to-end"))
    thin = [s["name"] for s in stages if s["count"] < min_stage_n]
    if thin:
        recs.append(_rec("data", "medium", f"Stages with < {min_stage_n} users: {thin}",
                         "Treat rates at these stages as directional; collect more data or use qualitative research (session recordings, interviews).",
                         "Small samples produce noisy conversion rates.", test="Wait for more traffic / run user interviews"))
    if f.get("largest_drop"):
        row = next(r for r in f["stages"] if r["name"] == f["largest_drop"])
        recs.append(_rec("drop_off", "high", f"Largest drop-off entering '{row['name']}' ({row['drop_off']:.0%} lost)",
                         f"Investigate the step before '{row['name']}': friction, unclear value, trust or mismatch with expectations.",
                         f"Reducing friction/uncertainty at '{row['name']}' increases step conversion.",
                         test="Session recordings + exit survey, then A/B test the top fix"))
    # message consistency
    for a, b in zip(stages, stages[1:]):
        if a.get("message") and b.get("message"):
            ov = T.jaccard(a["message"], b["message"])
            if ov < 0.15:
                recs.append(_rec("consistency", "medium", f"Message changes between '{a['name']}' and '{b['name']}' (overlap {ov:.0%})",
                                 f"Carry the promise from '{a['name']}' into '{b['name']}' (same outcome words, offer, visuals).",
                                 "Message continuity ('scent') reduces bounce from people who feel misled.",
                                 [a["message"][:80], b["message"][:80]]))
    # offer vs traffic
    src = (inp.get("traffic_source") or "").lower()
    first_cta = next((s.get("cta", "") for s in stages[1:] if s.get("cta")), "")
    if src in ("cold", "paid_social", "display", "tiktok", "meta") and T.contains_any(first_cta, HIGH_COMMITMENT_CTAS):
        recs.append(_rec("offer_traffic_match", "high", f"Cold traffic ({src}) is asked for a high-commitment action ('{first_cta}')",
                         "Offer a lower-commitment first step (demo, trial, guide, quiz) or warm the audience first.",
                         "Cold audiences are rarely ready to buy on first touch; a smaller ask raises first-step conversion.",
                         test="A/B test low- vs high-commitment CTA for cold traffic"))
    # trust before purchase
    for s in stages:
        if s["name"].lower() in ("purchase", "checkout", "pricing") and s.get("message") and \
                not any(re.search(p, s["message"].lower()) for p in PROOF_SIGNALS):
            recs.append(_rec("trust", "medium", f"No proof/trust element at '{s['name']}'",
                             "Add verified proof, guarantee terms (if real), security and refund info near the purchase action.",
                             "Perceived risk peaks at payment; visible trust reduces abandonment."))
    # activation
    names = [s["name"].lower() for s in stages]
    if "signup" in names and "activation" in names:
        i, j = names.index("signup"), names.index("activation")
        if stages[i]["count"]:
            rate = stages[j]["count"] / stages[i]["count"]
            if rate < 0.4:
                recs.append(_rec("activation", "high", f"Only {rate:.0%} of signups activate",
                                 "Shorten time-to-first-value: remove setup steps before the first win, add templates/sample data, onboarding checklist.",
                                 "Users who reach value quickly are more likely to convert and retain.",
                                 test="Cohort comparison of new onboarding vs old"))
    # follow-up vs objections
    if objections and follow_ups:
        joined = " ".join(follow_ups).lower()
        missed = [o for o in objections if not set(T.content_words(o)) & set(T.content_words(joined))]
        if missed:
            recs.append(_rec("follow_up", "medium", f"Follow-up messages don't address objections: {missed[:4]}",
                             "Add one follow-up per top objection with a truthful answer and evidence.",
                             "Leads stall on unanswered objections."))
    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: order[r["severity"]])
    return {"funnel": f, "recommendations": recs,
            "note": "Hypotheses to test, not guaranteed improvements."}


# ---------------------------------------------------------------- HTML audit
class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta = {}
        self.h1, self.h2 = [], []
        self.ctas, self.links, self.images, self.forms, self.inputs = [], [], [], [], []
        self.text_chunks: list[tuple[int, str]] = []
        self.styles, self.scripts = [], 0
        self._stack: list[str] = []
        self._cur_tag_text: list[str] = []
        self._capture: str | None = None
        self._capture_line = 0
        self._form_stack: list[dict] = []
        self.nav_links = 0
        self._in_nav = 0
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        self._stack.append(tag)
        if tag == "meta":
            if a.get("name"):
                self.meta[a["name"].lower()] = a.get("content", "")
        elif tag in ("h1", "h2", "title", "button", "a", "label"):
            self._capture, self._capture_line, self._cur_tag_text = tag, line, []
            self._cur_attrs = a
        elif tag == "img":
            self.images.append({"alt": a.get("alt"), "src": a.get("src"), "line": line,
                                "lazy": a.get("loading") == "lazy"})
        elif tag == "form":
            self._form_stack.append({"line": line, "fields": [], "action": a.get("action")})
        elif tag in ("input", "select", "textarea"):
            typ = a.get("type", "text" if tag == "input" else tag)
            if typ not in ("hidden", "submit", "button"):
                field = {"type": typ, "name": a.get("name") or a.get("id"), "required": "required" in a, "line": line}
                self.inputs.append(field)
                if self._form_stack:
                    self._form_stack[-1]["fields"].append(field)
            elif typ == "submit":
                self.ctas.append({"text": a.get("value", "submit"), "line": line, "tag": "input"})
        elif tag == "nav":
            self._in_nav += 1
        elif tag == "style":
            self._in_style = True
        elif tag == "script":
            self.scripts += 1

    def handle_endtag(self, tag):
        if self._stack and tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass
        if tag == self._capture:
            txt = " ".join("".join(self._cur_tag_text).split())
            line = self._capture_line
            if tag == "h1":
                self.h1.append((line, txt))
            elif tag == "h2":
                self.h2.append((line, txt))
            elif tag == "title":
                self.title = txt
            elif tag in ("button",):
                self.ctas.append({"text": txt, "line": line, "tag": tag})
            elif tag == "a":
                cls = (self._cur_attrs.get("class") or "") + " " + (self._cur_attrs.get("role") or "")
                self.links.append({"text": txt, "href": self._cur_attrs.get("href"), "line": line})
                if self._in_nav:
                    self.nav_links += 1
                if re.search(r"btn|button|cta", cls) or T.contains_any(txt, CTA_VERBS):
                    self.ctas.append({"text": txt, "line": line, "tag": "a"})
            self._capture = None
        if tag == "form" and self._form_stack:
            self.forms.append(self._form_stack.pop())
        if tag == "nav" and self._in_nav:
            self._in_nav -= 1
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.styles.append(data)
            return
        if self._stack and self._stack[-1] in ("script",):
            return
        if self._capture:
            self._cur_tag_text.append(data)
        if data.strip():
            self.text_chunks.append((self.getpos()[0], data.strip()))


def jsx_to_html(src: str) -> str:
    """Best-effort conversion of JSX/TSX/Vue/Svelte markup to parseable HTML."""
    s = re.sub(r"(?s)/\*.*?\*/", "", src)
    s = re.sub(r"(?m)^\s*import .*$", "", s)
    s = re.sub(r"\bexport (default )?", "", s)
    s = s.replace("className=", "class=").replace("htmlFor=", "for=")
    s = re.sub(r"\{/\*.*?\*/\}", "", s)
    s = re.sub(r"=\{\s*['\"]([^'\"]*)['\"]\s*\}", r'="\1"', s)
    s = re.sub(r"=\{[^{}]*\}", '="{expr}"', s)
    s = re.sub(r"\{[^{}<>]*\}", " ", s)
    return s


def audit_landing_html(source: str, filetype: str = "html", context: dict | None = None) -> dict:
    """source: HTML (or JSX/TSX/Vue/Svelte) string. context: {"offer": {...}, "ad_text": str,
    "audience_terms": [...], "primary_goal": "signup|purchase|lead|install"}"""
    ctx = context or {}
    html = source if filetype == "html" else jsx_to_html(source)
    p = _PageParser()
    p.feed(html)
    p.close()
    alltext = " ".join(t for _, t in p.text_chunks)
    low = alltext.lower()
    recs = []
    first_h2_line = p.h2[0][0] if p.h2 else 10 ** 9
    hero_text = " ".join(t for ln, t in p.text_chunks if ln < first_h2_line)[:1200]

    # hero / headline
    if not p.h1:
        recs.append(_rec("headline", "high", "No <h1> headline", "Add one H1 that states the outcome for the target customer.",
                         "A clear headline lets visitors decide in seconds whether the page is for them.", test="5-second test"))
    else:
        if len(p.h1) > 1:
            recs.append(_rec("headline", "low", f"{len(p.h1)} H1 elements", "Keep a single H1; use H2 for sections.",
                             "One primary message reduces cognitive load.", [h for _, h in p.h1][:3], p.h1[1][0]))
        line, h = p.h1[0]
        hw = len(T.words(h))
        if hw > 14:
            recs.append(_rec("headline", "medium", f"Headline is long ({hw} words)", "Cut to <= 10-12 words; move detail to the subheadline.",
                             "Short headlines are processed faster.", [h], line))
        if hw and not re.search(r"\d|\byou|\byour", h.lower()) and len(T.contains_any(h, ["best", "solution", "platform", "innovative", "welcome"])):
            recs.append(_rec("headline", "medium", "Headline is generic/product-centric", "State the specific outcome for the reader (in their words).",
                             "Outcome-focused headlines increase relevance.", [h], line))
        if ctx.get("ad_text"):
            ov = len(set(T.content_words(ctx["ad_text"])) & set(T.content_words(h + " " + hero_text))) / max(1, len(set(T.content_words(ctx["ad_text"]))))
            if ov < 0.3:
                recs.append(_rec("message_match", "high", f"Hero doesn't echo the ad (overlap {ov:.0%})", "Repeat the ad's promise/offer in the H1 or subheadline.",
                                 "Visitors who don't see what they clicked for bounce.", [h], line))
    if filetype == "html" and not p.meta.get("description"):
        recs.append(_rec("seo_snippet", "low", "Missing meta description", "Add a meta description that mirrors the headline promise.",
                         "Improves search snippet relevance and CTR.", test="Search Console CTR before/after"))

    # CTA
    hero_ctas = [c for c in p.ctas if c["line"] < first_h2_line]
    if not p.ctas:
        recs.append(_rec("cta", "high", "No call-to-action button/link found", "Add one primary CTA describing the action and outcome.",
                         "Without a clear next step, interested visitors leave.", test="A/B test"))
    else:
        if not hero_ctas:
            recs.append(_rec("cta", "high", "No CTA in the hero section", "Place the primary CTA in the hero (above the first section break).",
                             "Visitors ready to act shouldn't need to scroll.", [c["text"] for c in p.ctas[:2]], p.ctas[0]["line"]))
        generic = [c for c in p.ctas if c["text"].strip().lower() in ("submit", "click here", "go", "send", "continue", "learn more", "")]
        if generic:
            recs.append(_rec("cta", "medium", f"Generic CTA text: {[c['text'] for c in generic][:3]}",
                             "Use action + value text, e.g. 'Get my free quote', 'Start 14-day trial'.",
                             "Specific CTA text clarifies what happens next.", [c["text"] for c in generic], generic[0]["line"]))
        distinct = {c["text"].strip().lower() for c in p.ctas if c["text"].strip()}
        if len(distinct) > 4:
            recs.append(_rec("cta", "medium", f"{len(distinct)} different CTAs compete for attention",
                             "Pick one primary action; demote secondary links.", "Fewer choices reduce decision friction.", sorted(distinct)[:6]))

    # proof / trust
    proof_hits = [pat for pat in PROOF_SIGNALS if re.search(pat, low)]
    if not proof_hits:
        recs.append(_rec("proof_trust", "high", "No social proof or evidence on the page",
                         "Add verified proof: real reviews with source, customer logos (with permission), data, demo video.",
                         "Proof reduces perceived risk, especially for new brands."))
    if p.forms and not T.contains_any(low, ["privacy", "spam", "secure", "unsubscribe", "we never share"]):
        recs.append(_rec("proof_trust", "low", "No privacy/spam reassurance near forms", "Add a short privacy note under the form.",
                         "Reassurance reduces form anxiety.", line=p.forms[0]["line"]))

    # offer clarity
    if ctx.get("offer"):
        o = ctx["offer"]
        pv = float(o["price"]) if o.get("price") is not None else None
        pstr = (str(int(pv)) if pv is not None and pv.is_integer() else f"{pv:.2f}") if pv is not None else None
        if pstr and not re.search(re.escape(pstr), alltext):
            recs.append(_rec("offer_clarity", "medium", "Offer price not shown on page", "State price (or 'from') and what's included, or explain why pricing is on request.",
                             "Hidden pricing raises uncertainty for price-sensitive buyers."))
        missing = [d for d in o.get("deliverables", []) if not set(T.content_words(d)) & set(T.content_words(alltext))]
        if missing:
            recs.append(_rec("offer_clarity", "medium", f"Deliverables not mentioned: {missing[:4]}", "List what the buyer gets.",
                             "Concrete inclusions increase perceived value."))
    if not T.contains_any(hero_text, ["you", "your"]) and hero_text:
        recs.append(_rec("offer_clarity", "low", "Hero copy doesn't address the reader", "Rewrite hero around the reader's outcome ('you').",
                         "Reader-centred copy increases relevance."))

    # forms / signup friction
    for form in p.forms:
        n = len(form["fields"])
        if n > 5:
            recs.append(_rec("forms", "high" if n > 8 else "medium", f"Form has {n} fields",
                             "Ask only what's needed now; move the rest to after signup (progressive profiling).",
                             "Each extra field adds effort and drop-off risk.", [f["name"] for f in form["fields"]], form["line"]))
        if any(f["type"] == "password" for f in form["fields"]) and any(f["name"] and "confirm" in f["name"].lower() for f in form["fields"]):
            recs.append(_rec("signup_friction", "low", "Password confirmation field", "Use a show/hide toggle instead of confirm-password.",
                             "Removes a redundant field.", line=form["line"]))
        if any((f["name"] or "").lower() in ("phone", "tel", "phone_number") or f["type"] == "tel" for f in form["fields"]) and n <= 4:
            recs.append(_rec("forms", "low", "Phone number requested on a short form", "Make phone optional unless you call every lead.",
                             "Phone fields deter some users.", line=form["line"]))

    # mobile
    if filetype == "html" and "viewport" not in p.meta:
        recs.append(_rec("mobile", "high", "No viewport meta tag", 'Add <meta name="viewport" content="width=device-width, initial-scale=1">.',
                         "Without it, mobile browsers render a zoomed-out desktop page.", test="Check on real devices"))
    css = " ".join(p.styles)
    if css and "@media" not in css and filetype == "html":
        recs.append(_rec("mobile", "low", "Inline CSS has no media queries", "Confirm the layout is responsive (external CSS or utility classes).",
                         "Non-responsive layouts hurt mobile conversion."))
    small = re.findall(r"font-size:\s*(1[0-3]|[0-9])px", css)
    if small:
        recs.append(_rec("mobile", "low", f"Small font sizes in CSS: {sorted(set(small))}px", "Use >= 16px body text on mobile.",
                         "Small text is hard to read on phones."))

    # pricing / checkout
    prices = re.findall(r"[$€£]\s?\d[\d,]*(?:\.\d\d)?", alltext)
    if len(set(prices)) >= 3 and not T.contains_any(low, ["most popular", "recommended", "best value"]):
        recs.append(_rec("pricing", "low", "Several price points without a highlighted plan", "Highlight the plan most buyers should choose.",
                         "A recommended option reduces decision fatigue.", sorted(set(prices))[:5]))
    if T.contains_any(low, ["checkout", "cart"]) and not T.contains_any(low, ["guest", "apple pay", "google pay", "paypal"]):
        recs.append(_rec("checkout", "low", "No sign of guest checkout or express payment", "Offer guest checkout and express wallets if available.",
                         "Forced account creation is a common abandonment reason."))

    # distractions / performance / accessibility
    if p.nav_links > 7 and ctx.get("primary_goal") in ("signup", "purchase", "lead"):
        recs.append(_rec("distraction", "low", f"{p.nav_links} navigation links on a conversion page", "Reduce nav on paid-traffic landing pages.",
                         "Exit links pull visitors away from the goal."))
    no_alt = [i for i in p.images if not i["alt"]]
    if no_alt:
        recs.append(_rec("accessibility", "low", f"{len(no_alt)} image(s) without alt text", "Add descriptive alt text.",
                         "Accessibility and image-search benefits.", [i["src"] for i in no_alt][:3], no_alt[0]["line"]))
    if p.scripts > 15:
        recs.append(_rec("performance", "medium", f"{p.scripts} script tags", "Audit third-party scripts; defer non-critical ones.",
                         "Slow pages lose visitors, especially on mobile.", test="Lighthouse / Core Web Vitals"))
    if ctx.get("audience_terms") and not T.contains_any(alltext, ctx["audience_terms"]):
        recs.append(_rec("audience_fit", "medium", "Page doesn't use the customer's own terms", f"Work in: {ctx['audience_terms'][:5]}",
                         "Customer language increases perceived relevance."))

    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: order[r["severity"]])
    return {
        "summary": {"title": p.title, "h1": [h for _, h in p.h1], "h2_count": len(p.h2), "ctas": [c["text"] for c in p.ctas][:10],
                    "forms": [{"line": f["line"], "fields": len(f["fields"])} for f in p.forms], "images": len(p.images),
                    "word_count": len(T.words(alltext)), "proof_signals": len(proof_hits), "has_viewport": "viewport" in p.meta},
        "recommendations": recs,
        "limitations": (["JSX/Vue/Svelte parsed heuristically: dynamic content and components rendered elsewhere are not seen."]
                        if filetype != "html" else []) + ["Static analysis only: no rendering, speed or real-user data."],
        "note": "Each recommendation is a hypothesis; validate with tests or user research.",
    }


def audit_file(path: str, context: dict | None = None) -> dict:
    ext = Path(path).suffix.lower().lstrip(".")
    ft = "html" if ext in ("html", "htm") else "jsx"
    return audit_landing_html(Path(path).read_text(errors="replace"), ft, context)


# ---------------------------------------------------------------- onboarding
def audit_onboarding(spec: dict) -> dict:
    """spec: {"steps": [{"name", "fields": int, "optional": bool, "delivers_value": bool, "est_seconds": int}],
    "activation_event": str, "progress_indicator": bool, "social_login": bool,
    "email_verification_before_value": bool, "paywall": "before_value"|"after_value"|"none",
    "upgrade_prompts": [{"trigger": str, "copy": str}], "empty_states_have_guidance": bool}"""
    steps = spec.get("steps", [])
    recs = []
    first_value = next((i for i, s in enumerate(steps) if s.get("delivers_value")), None)
    before = steps[:first_value] if first_value is not None else steps
    secs = sum(s.get("est_seconds", 0) for s in before)
    if not spec.get("activation_event"):
        recs.append(_rec("activation", "high", "No activation event defined", "Define the action that predicts retention (e.g. 'first job scheduled').",
                         "You can't improve activation you don't measure.", test="Correlate early actions with week-4 retention"))
    if first_value is None:
        recs.append(_rec("time_to_value", "high", "No step delivers value", "Introduce a quick win early (template, sample data, instant result).",
                         "Users who see value early are more likely to continue."))
    else:
        req = [s["name"] for s in before if not s.get("optional")]
        if len(req) > 3 or secs > 180:
            recs.append(_rec("time_to_value", "high", f"{len(req)} required steps / ~{secs}s before first value",
                             "Defer non-essential steps until after the first win; make them optional.",
                             "Shorter time-to-value raises activation.", req))
    fields = sum(s.get("fields", 0) for s in before)
    if fields > 6:
        recs.append(_rec("signup_friction", "medium", f"{fields} form fields before value", "Collect only email/password (or SSO) up front.",
                         "Fewer fields reduce signup abandonment."))
    if spec.get("email_verification_before_value"):
        recs.append(_rec("signup_friction", "medium", "Email verification required before any value",
                         "Let users in first; verify later (before sensitive actions).", "Context switching to email loses users."))
    if not spec.get("social_login") and spec.get("audience_type") in ("consumer", "prosumer"):
        recs.append(_rec("signup_friction", "low", "No social/SSO login", "Offer Google/Apple sign-in if appropriate.",
                         "One-tap signup reduces effort."))
    if len(steps) > 3 and not spec.get("progress_indicator"):
        recs.append(_rec("onboarding", "low", "Multi-step onboarding without progress indicator", "Show steps remaining.",
                         "Visible progress reduces abandonment in multi-step flows."))
    if spec.get("paywall") == "before_value":
        recs.append(_rec("upgrade_flow", "high", "Paywall appears before the user experiences value",
                         "Move the paywall after the first success, or offer a trial/limited free tier.",
                         "Users pay for value they've felt; early paywalls lower trial-to-paid for unknown products.",
                         test="A/B test paywall placement (with approval)"))
    for up in spec.get("upgrade_prompts", []):
        trig = (up.get("trigger") or "").lower()
        if trig in ("on_login", "random", "time_based", "every_session"):
            recs.append(_rec("upgrade_flow", "medium", f"Upgrade prompt on '{trig}'", "Trigger upgrades at moments of need (hit a limit, use a premium feature).",
                             "Contextual prompts feel helpful rather than nagging.", [up.get("copy", "")[:80]]))
        if up.get("copy") and not T.contains_any(up["copy"], ["you", "your", "unlock", "get", "keep"]):
            recs.append(_rec("upgrade_flow", "low", "Upgrade copy doesn't state the user benefit", "Say what they get / keep by upgrading.",
                             "Benefit-led prompts clarify value.", [up["copy"][:80]]))
    if spec.get("empty_states_have_guidance") is False:
        recs.append(_rec("activation", "medium", "Empty states lack guidance", "Add next-step prompts and sample content to empty screens.",
                         "Blank screens stall new users."))
    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: order[r["severity"]])
    return {"steps_before_value": len(before), "seconds_before_value": secs, "recommendations": recs}


def to_record(audit: dict, title: str, product: str | None = None) -> dict:
    return {"kind": "funnel_audit", "title": title[:300], "product": product, "basis": "inferred", "confidence": "medium",
            "tags": ["audit"], "data": audit}
