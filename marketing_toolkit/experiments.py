"""Experiment management + statistics.

Statistics (stdlib only):
- two-proportion z-test, Wilson score intervals, difference CI
- sample size per arm for a two-proportion test (given baseline, MDE, alpha, power)
- Holm-Bonferroni correction for several variants
- decision rules that refuse to declare a winner on small or unreliable data
  (minimum conversions/visitors per arm, planned sample reached, practical
  significance vs the minimum detectable effect, guardrail metrics).

ExperimentManager stores experiments in the KnowledgeStore (kind=experiment),
keeps every update in history, and records failed/inconclusive tests with
their lessons (kind=approach).
"""

from __future__ import annotations

import math
from datetime import date

from .config import load_config
from .schemas import EXPERIMENT, validate
from .store import ConflictError, KnowledgeStore


# ---------------------------------------------------------------- distributions
def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p: float) -> float:
    """Inverse normal CDF (Acklam's rational approximation, |error| < 1.2e-9 after refinement)."""
    if not 0 < p < 1:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p > 1 - pl:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    # one Newton refinement step
    e = norm_cdf(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


# ---------------------------------------------------------------- tests
def wilson_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be > 0")
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    z = norm_ppf(1 - alpha / 2)
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def two_proportion_test(c_conv: int, c_n: int, v_conv: int, v_n: int, alpha: float = 0.05) -> dict:
    for name, val in (("control conversions", c_conv), ("control n", c_n), ("variant conversions", v_conv), ("variant n", v_n)):
        if not isinstance(val, (int, float)) or val < 0:
            raise ValueError(f"{name} must be a non-negative number")
    if c_n == 0 or v_n == 0:
        raise ValueError("each arm needs n > 0")
    if c_conv > c_n or v_conv > v_n:
        raise ValueError("conversions cannot exceed sample size")
    p1, p2 = c_conv / c_n, v_conv / v_n
    pooled = (c_conv + v_conv) / (c_n + v_n)
    se_pool = math.sqrt(pooled * (1 - pooled) * (1 / c_n + 1 / v_n))
    z = (p2 - p1) / se_pool if se_pool > 0 else 0.0
    p_value = 2 * (1 - norm_cdf(abs(z)))
    se_diff = math.sqrt(p1 * (1 - p1) / c_n + p2 * (1 - p2) / v_n)
    zc = norm_ppf(1 - alpha / 2)
    return {
        "control_rate": p1, "variant_rate": p2, "absolute_diff": p2 - p1,
        "relative_lift": (p2 - p1) / p1 if p1 > 0 else None,
        "z": z, "p_value": p_value,
        "diff_ci": (p2 - p1 - zc * se_diff, p2 - p1 + zc * se_diff),
        "control_ci": wilson_interval(int(c_conv), int(c_n), alpha),
        "variant_ci": wilson_interval(int(v_conv), int(v_n), alpha),
        "alpha": alpha,
    }


def sample_size_per_arm(baseline_rate: float, mde_relative: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Visitors per arm to detect a relative lift of mde_relative over baseline_rate (two-sided)."""
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be in (0,1)")
    if mde_relative <= 0:
        raise ValueError("mde_relative must be > 0")
    p1 = baseline_rate
    p2 = p1 * (1 + mde_relative)
    if p2 >= 1:
        raise ValueError("baseline x (1+MDE) must be < 1")
    za, zb = norm_ppf(1 - alpha / 2), norm_ppf(power)
    pbar = (p1 + p2) / 2
    n = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2
    return math.ceil(n)


def holm_correction(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    out, still = {}, True
    for i, (k, p) in enumerate(items):
        threshold = alpha / (m - i)
        sig = still and p <= threshold
        if not sig:
            still = False
        out[k] = {"p_value": p, "holm_threshold": threshold, "significant": sig}
    return out


def analyze(arms: dict[str, dict], control: str, mde_relative: float | None = None, planned_n_per_arm: int | None = None,
            guardrails: dict[str, dict] | None = None, config: dict | None = None) -> dict:
    """arms: {"control": {"n": visitors, "conversions": k}, "B": {...}, ...}.
    guardrails: {"refund_rate": {"control": x, "B": y, "max_increase": 0.01}} (absolute)."""
    cfg = load_config(config)
    alpha = cfg["alpha"]
    if control not in arms:
        raise ValueError("control arm missing")
    c = arms[control]
    results, pvals, reasons = {}, {}, []
    for name, a in arms.items():
        if name == control:
            continue
        t = two_proportion_test(c["conversions"], c["n"], a["conversions"], a["n"], alpha)
        results[name] = t
        pvals[name] = t["p_value"]
    corrected = holm_correction(pvals, alpha) if len(pvals) > 1 else {k: {"p_value": v, "holm_threshold": alpha, "significant": v <= alpha} for k, v in pvals.items()}

    # data sufficiency
    insufficient = []
    for name, a in arms.items():
        if a["n"] < cfg["min_visitors_per_arm"] or a["conversions"] < cfg["min_conversions_per_arm"]:
            insufficient.append(name)
    if insufficient:
        reasons.append(f"Insufficient data in {insufficient}: need >= {cfg['min_visitors_per_arm']} visitors and "
                       f">= {cfg['min_conversions_per_arm']} conversions per arm.")
    if planned_n_per_arm and any(a["n"] < planned_n_per_arm for a in arms.values()):
        reasons.append(f"Planned sample of {planned_n_per_arm}/arm not reached: stopping early inflates false positives.")

    guard_fail = []
    for gname, g in (guardrails or {}).items():
        for name in results:
            if name in g and control in g and g[name] - g[control] > g.get("max_increase", 0):
                guard_fail.append(f"{gname} worsened for {name} ({g[control]} -> {g[name]})")

    decisions = {}
    for name, t in results.items():
        sig = corrected[name]["significant"]
        practical = mde_relative is None or (t["relative_lift"] is not None and abs(t["relative_lift"]) >= mde_relative)
        if reasons:
            d = "keep_running" if planned_n_per_arm else "inconclusive"
        elif any(name in gf for gf in guard_fail):
            d = "reject_variant_guardrail"
        elif sig and t["absolute_diff"] > 0 and practical:
            d = "variant_wins"
        elif sig and t["absolute_diff"] < 0:
            d = "control_wins"
        elif sig and not practical:
            d = "significant_but_not_practical"
        else:
            d = "no_detectable_difference"
        decisions[name] = d
    return {"control": control, "comparisons": results, "multiple_comparison": corrected,
            "decisions": decisions, "data_warnings": reasons, "guardrail_failures": guard_fail,
            "assumptions": ["Independent visitors, randomly assigned", "Fixed-horizon test (no peeking/optional stopping)",
                            "Binary conversion metric", f"alpha={alpha}, two-sided; Holm correction when >1 variant"]}


# ---------------------------------------------------------------- manager
class ExperimentManager:
    def __init__(self, store: KnowledgeStore, config: dict | None = None):
        self.store, self.cfg = store, load_config(config)

    def create(self, spec: dict, product: str | None = None, if_exists: str = "error") -> str:
        """if_exists: 'error' (default) raises ConflictError when experiment_id already exists
        with different content; 'return' returns the existing experiment's id unchanged."""
        spec = dict(spec)
        spec.setdefault("status", "draft")
        spec.setdefault("guardrail_metrics", [])
        validate(spec, EXPERIMENT)
        if spec.get("baseline_rate") and spec.get("minimum_detectable_effect"):
            spec["planned_n_per_arm"] = sample_size_per_arm(spec["baseline_rate"], spec["minimum_detectable_effect"],
                                                            self.cfg["alpha"], self.cfg["power"])
        rec = {"kind": "experiment", "title": f"[{spec.get('category', 'other')}] {spec['hypothesis']}"[:300],
               "product": product, "audience": spec.get("target_audience"), "basis": "hypothesis", "confidence": "low",
               "tags": ["experiment", spec.get("category", "other"), spec["funnel_stage"]],
               "data": spec}
        if spec.get("experiment_id"):
            rec["natural_key"] = spec["experiment_id"]
        try:
            rid, action = self.store.add(rec)
        except ConflictError as e:
            if if_exists == "return":
                return e.existing_id
            raise
        if action == "duplicate":
            return rid
        if not spec.get("experiment_id"):
            self.store.update(rid, {"natural_key": rid, "data": {"experiment_id": rid}}, "assign id")
        return rid

    def get(self, eid: str) -> dict:
        r = self.store.get(eid)
        if not r or r["kind"] != "experiment":
            raise KeyError(eid)
        return r

    def start(self, eid: str, start_date: str | None = None) -> dict:
        return self.store.update(eid, {"data": {"status": "running", "start_date": start_date or date.today().isoformat()}}, "started")

    def record_data(self, eid: str, arms: dict[str, dict], guardrails: dict | None = None, source: str = "manual") -> dict:
        """arms counts must come from real tracking data; source documents where."""
        for name, a in arms.items():
            if not {"n", "conversions"} <= set(a):
                raise ValueError(f"arm {name} needs n and conversions")
        return self.store.update(eid, {"data": {"arms": arms, "guardrail_data": guardrails or {}, "data_source": source}},
                                 f"data recorded from {source}")

    def analyze(self, eid: str, control_name: str = "control") -> dict:
        exp = self.get(eid)["data"]
        if "arms" not in exp:
            raise ValueError("no data recorded yet")
        return analyze(exp["arms"], control_name, exp.get("minimum_detectable_effect"), exp.get("planned_n_per_arm"),
                       exp.get("guardrail_data"), self.cfg)

    def conclude(self, eid: str, decision: str, learnings: str, follow_up: str = "", control_name: str = "control") -> dict:
        """Store the analysis, decision and learnings. Losing / inconclusive tests are also
        saved as 'approach' records so future work doesn't repeat them."""
        exp = self.get(eid)
        analysis = self.analyze(eid, control_name) if "arms" in exp["data"] else None
        status = "completed" if analysis and not analysis["data_warnings"] else "inconclusive"
        updated = self.store.update(eid, {"status": "active", "data": {
            "status": status, "end_date": exp["data"].get("end_date") or date.today().isoformat(),
            "results": analysis, "decision": decision, "learnings": learnings, "follow_up": follow_up}},
            f"concluded: {decision}")
        outcome = "failed" if decision in ("control_wins", "no_detectable_difference", "reject_variant_guardrail", "inconclusive") else "succeeded"
        self.store.add({
            "kind": "approach", "title": f"{outcome.upper()}: {exp['data']['hypothesis']}"[:300], "product": exp.get("product"),
            "audience": exp.get("audience"), "basis": "measured" if status == "completed" else "hypothesis",
            "confidence": "medium" if status == "completed" else "low", "tags": ["learning", outcome, exp["data"].get("category", "other")],
            "sources": [eid], "natural_key": f"learning|{eid}",
            "data": {"experiment_id": eid, "outcome": outcome, "decision": decision, "learnings": learnings,
                     "follow_up": follow_up, "control": exp["data"]["control"], "variant": exp["data"]["variant"]}},
            on_conflict="version")
        return updated

    def failed_tests(self, product: str | None = None) -> list[dict]:
        return self.store.find(kind="approach", product=product, tag="failed")
