"""Marketing analytics and unit economics.

Every function returns a MetricResult-like dict:
    {"metric", "value", "ok", "error", "inputs", "formula", "note"}
Invalid input (missing, negative, zero denominators, impossible ratios)
never raises in normal use: it returns ok=False with an explanation, so a
dashboard or Claude can show *why* a number is unavailable.

Revenue is never treated as profit: roas() reports revenue/spend, while
profit metrics (contribution, poas, breakeven_roas) need margin data.
"""

from __future__ import annotations

import math


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _res(metric, value=None, error=None, inputs=None, formula="", note="", unit=""):
    ok = error is None and value is not None
    if ok and isinstance(value, float):
        value = round(value, 6)
    return {"metric": metric, "value": value if ok else None, "ok": ok, "error": error, "inputs": inputs or {},
            "formula": formula, "note": note, "unit": unit}


def _ratio(metric, num, den, formula, unit="ratio", note="", allow_gt1=True, num_name="numerator", den_name="denominator"):
    inputs = {num_name: num, den_name: den}
    for name, v in inputs.items():
        if v is None:
            return _res(metric, error=f"missing {name}", inputs=inputs, formula=formula)
        if not _num(v):
            return _res(metric, error=f"{name} is not a number: {v!r}", inputs=inputs, formula=formula)
        if v < 0:
            return _res(metric, error=f"{name} is negative ({v})", inputs=inputs, formula=formula)
    if den == 0:
        return _res(metric, error=f"{den_name} is zero", inputs=inputs, formula=formula)
    val = num / den
    if not allow_gt1 and val > 1:
        return _res(metric, error=f"inconsistent data: {num_name} ({num}) > {den_name} ({den})", inputs=inputs, formula=formula)
    return _res(metric, val, inputs=inputs, formula=formula, unit=unit, note=note)


# ---------------------------------------------------------------- acquisition
def ctr(clicks, impressions):
    return _ratio("ctr", clicks, impressions, "clicks / impressions", "rate", allow_gt1=False, num_name="clicks", den_name="impressions")


def cpc(spend, clicks):
    return _ratio("cpc", spend, clicks, "spend / clicks", "currency", num_name="spend", den_name="clicks")


def cpm(spend, impressions):
    r = _ratio("cpm", spend, impressions, "spend / impressions * 1000", "currency", num_name="spend", den_name="impressions")
    if r["ok"]:
        r["value"] = round(r["value"] * 1000, 6)
    return r


def cpl(spend, leads):
    return _ratio("cpl", spend, leads, "spend / leads", "currency", num_name="spend", den_name="leads")


def conversion_rate(conversions, visitors, metric="conversion_rate"):
    return _ratio(metric, conversions, visitors, "conversions / visitors", "rate", allow_gt1=False,
                  num_name="conversions", den_name="visitors")


def lead_to_customer(customers, leads):
    return _ratio("lead_to_customer", customers, leads, "customers / leads", "rate", allow_gt1=False,
                  num_name="customers", den_name="leads")


def cac(total_acquisition_cost, new_customers):
    return _ratio("cac", total_acquisition_cost, new_customers, "(ad spend + sales & marketing costs) / new customers",
                  "currency", note="Include all acquisition costs (tools, salaries, agency), not only ad spend.",
                  num_name="total_acquisition_cost", den_name="new_customers")


def cpa(spend, acquisitions):
    return _ratio("cpa", spend, acquisitions, "spend / acquisitions (conversion events)", "currency",
                  note="CPA counts the tracked conversion event; it is usually narrower than CAC.",
                  num_name="spend", den_name="acquisitions")


def roas(revenue, spend):
    r = _ratio("roas", revenue, spend, "attributed revenue / ad spend", "ratio", num_name="revenue", den_name="spend")
    r["note"] = "ROAS is revenue, not profit. Compare against breakeven_roas() before calling a campaign profitable."
    return r


def breakeven_roas(gross_margin):
    if not _num(gross_margin):
        return _res("breakeven_roas", error="gross_margin missing or not a number", inputs={"gross_margin": gross_margin})
    if not 0 < gross_margin <= 1:
        return _res("breakeven_roas", error="gross_margin must be in (0, 1]", inputs={"gross_margin": gross_margin})
    return _res("breakeven_roas", 1 / gross_margin, inputs={"gross_margin": gross_margin}, formula="1 / gross margin",
                note="ROAS below this loses money on first purchase (before fixed costs).")


def poas(gross_profit, spend):
    return _ratio("poas", gross_profit, spend, "gross profit from attributed orders / ad spend", "ratio",
                  num_name="gross_profit", den_name="spend")


def revenue_per_visitor(revenue, visitors):
    return _ratio("revenue_per_visitor", revenue, visitors, "revenue / visitors", "currency", num_name="revenue", den_name="visitors")


def aov(revenue, orders):
    return _ratio("aov", revenue, orders, "revenue / orders", "currency", num_name="revenue", den_name="orders")


# ---------------------------------------------------------------- profitability
def gross_margin(revenue, cogs):
    if revenue is None or cogs is None or not (_num(revenue) and _num(cogs)):
        return _res("gross_margin", error="revenue and cogs required as numbers", inputs={"revenue": revenue, "cogs": cogs})
    if revenue <= 0:
        return _res("gross_margin", error="revenue must be > 0", inputs={"revenue": revenue, "cogs": cogs})
    if cogs < 0:
        return _res("gross_margin", error="cogs is negative", inputs={"revenue": revenue, "cogs": cogs})
    return _res("gross_margin", (revenue - cogs) / revenue, inputs={"revenue": revenue, "cogs": cogs},
                formula="(revenue - COGS) / revenue", unit="rate",
                note="Negative means each sale loses money before marketing." if cogs > revenue else "")


def contribution_margin(revenue, variable_costs, acquisition_cost=0.0):
    inputs = {"revenue": revenue, "variable_costs": variable_costs, "acquisition_cost": acquisition_cost}
    if any(v is None or not _num(v) for v in inputs.values()):
        return _res("contribution_margin", error="revenue, variable_costs, acquisition_cost must be numbers", inputs=inputs)
    if revenue <= 0:
        return _res("contribution_margin", error="revenue must be > 0", inputs=inputs)
    cm = revenue - variable_costs - acquisition_cost
    r = _res("contribution_margin", cm, inputs=inputs, formula="revenue - variable costs - acquisition cost", unit="currency")
    r["rate"] = round(cm / revenue, 6)
    return r


def churn_rate(customers_lost, customers_at_start):
    return _ratio("churn_rate", customers_lost, customers_at_start, "customers lost in period / customers at start",
                  "rate", allow_gt1=False, num_name="customers_lost", den_name="customers_at_start")


def retention_rate(customers_end, new_customers, customers_start):
    inputs = {"customers_end": customers_end, "new_customers": new_customers, "customers_start": customers_start}
    if any(v is None or not _num(v) or v < 0 for v in inputs.values()):
        return _res("retention_rate", error="all inputs must be non-negative numbers", inputs=inputs)
    if customers_start == 0:
        return _res("retention_rate", error="customers_start is zero", inputs=inputs)
    val = (customers_end - new_customers) / customers_start
    if val < 0 or val > 1:
        return _res("retention_rate", error=f"inconsistent counts give retention {val:.2f} (outside 0-1)", inputs=inputs)
    return _res("retention_rate", val, inputs=inputs, formula="(end - new) / start", unit="rate")


def ltv(arpu_per_period, gross_margin_rate, churn_per_period, max_periods=None):
    """Simple LTV = ARPU x gross margin / churn (gross-profit LTV, not revenue).
    With max_periods it caps the lifetime (sum of a geometric series)."""
    inputs = {"arpu_per_period": arpu_per_period, "gross_margin_rate": gross_margin_rate, "churn_per_period": churn_per_period}
    if any(v is None or not _num(v) for v in inputs.values()):
        return _res("ltv", error="arpu, gross margin and churn are required numbers", inputs=inputs)
    if arpu_per_period < 0:
        return _res("ltv", error="arpu is negative", inputs=inputs)
    if not 0 < gross_margin_rate <= 1:
        return _res("ltv", error="gross_margin_rate must be in (0, 1]", inputs=inputs)
    if not 0 < churn_per_period <= 1:
        return _res("ltv", error="churn_per_period must be in (0, 1] (0 churn gives infinite LTV: cap with max_periods)", inputs=inputs)
    gp = arpu_per_period * gross_margin_rate
    if max_periods:
        r = 1 - churn_per_period
        val = gp * (1 - r ** max_periods) / (1 - r) if r != 1 else gp * max_periods
        formula = "ARPU x GM x (1-(1-churn)^n)/churn"
    else:
        val = gp / churn_per_period
        formula = "ARPU x GM / churn"
    return _res("ltv", val, inputs=inputs, formula=formula, unit="currency",
                note="Gross-profit LTV. Assumes constant churn; early-cohort churn is usually higher.")


def ltv_to_cac(ltv_value, cac_value):
    r = _ratio("ltv_to_cac", ltv_value, cac_value, "LTV / CAC", "ratio", num_name="ltv", den_name="cac")
    if r["ok"]:
        r["note"] = "Rule of thumb: >3 healthy, 1-3 thin, <1 losing money (context-dependent)."
    return r


def payback_months(cac_value, monthly_gross_profit_per_customer, monthly_churn=None):
    inputs = {"cac": cac_value, "monthly_gross_profit_per_customer": monthly_gross_profit_per_customer}
    if any(v is None or not _num(v) for v in inputs.values()):
        return _res("payback_months", error="cac and monthly gross profit required", inputs=inputs)
    if cac_value < 0:
        return _res("payback_months", error="cac is negative", inputs=inputs)
    if monthly_gross_profit_per_customer <= 0:
        return _res("payback_months", error="monthly gross profit <= 0: CAC is never paid back", inputs=inputs)
    m = cac_value / monthly_gross_profit_per_customer
    r = _res("payback_months", m, inputs=inputs, formula="CAC / monthly gross profit per customer", unit="months")
    if monthly_churn and _num(monthly_churn) and 0 < monthly_churn < 1:
        expected_life = 1 / monthly_churn
        r["note"] = f"Expected customer life ~{expected_life:.1f} months." + (
            " Payback exceeds expected life: unprofitable on average." if m > expected_life else "")
    return r


# ---------------------------------------------------------------- funnel
def funnel(stages: list[dict]) -> dict:
    """stages: [{"name", "count"}...] in order. Returns step and cumulative conversion,
    drop-off and data problems (a stage larger than the previous one)."""
    out, problems = [], []
    if not stages or len(stages) < 2:
        return {"ok": False, "error": "need at least two stages", "stages": []}
    for i, s in enumerate(stages):
        c = s.get("count")
        if c is None or not _num(c) or c < 0:
            problems.append(f"stage '{s.get('name')}' has invalid count {c!r}")
    if problems:
        return {"ok": False, "error": "; ".join(problems), "stages": []}
    top = stages[0]["count"]
    for i, s in enumerate(stages):
        row = {"name": s["name"], "count": s["count"]}
        if i:
            prev = stages[i - 1]["count"]
            if s["count"] > prev:
                problems.append(f"'{s['name']}' ({s['count']}) > previous stage '{stages[i - 1]['name']}' ({prev}): "
                                "check tracking or stage order")
            row["step_conversion"] = round(s["count"] / prev, 6) if prev else None
            row["drop_off"] = round(1 - s["count"] / prev, 6) if prev else None
            row["cumulative_conversion"] = round(s["count"] / top, 6) if top else None
        out.append(row)
    valid = [r for r in out[1:] if r.get("drop_off") is not None]
    worst = max(valid, key=lambda r: r["drop_off"]) if valid else None
    return {"ok": not problems, "error": "; ".join(problems) or None, "stages": out,
            "largest_drop": worst["name"] if worst else None,
            "overall_conversion": round(stages[-1]["count"] / top, 6) if top else None}


# ---------------------------------------------------------------- scenarios
def unit_economics(price, cogs_per_order, orders_per_customer, cac_value, monthly=False, churn=None):
    """Per-customer economics. If monthly=True, price is a monthly subscription and churn is monthly."""
    res = {}
    gm = gross_margin(price, cogs_per_order)
    res["gross_margin"] = gm
    if not gm["ok"]:
        return {"ok": False, "error": gm["error"], **res}
    gp_order = price - cogs_per_order
    gm_raw = gp_order / price
    if monthly:
        lt = ltv(price, gm_raw, churn) if churn else _res("ltv", error="churn required for subscription LTV")
        res["ltv"] = lt
        res["payback"] = payback_months(cac_value, gp_order, churn)
        lifetime_gp = lt["value"] if lt["ok"] else None
    else:
        lifetime_gp = gp_order * (orders_per_customer or 1)
        res["ltv"] = _res("ltv", lifetime_gp, formula="(price - cogs) x orders per customer", unit="currency")
    res["ltv_to_cac"] = ltv_to_cac(lifetime_gp, cac_value) if lifetime_gp is not None else _res("ltv_to_cac", error="ltv unavailable")
    res["profit_per_customer"] = round(lifetime_gp - cac_value, 2) if lifetime_gp is not None and _num(cac_value) else None
    res["breakeven_roas"] = breakeven_roas(gm_raw) if gm_raw > 0 else _res("breakeven_roas", error="non-positive margin")
    res["ok"] = True
    return res


def scenarios(base: dict, changes: dict[str, dict]) -> dict:
    """base: kwargs for unit_economics(). changes: {"name": {param: new_value or "+10%"/"-20%"}}.
    Returns each scenario's profit_per_customer and LTV:CAC vs base."""
    def apply(params, ch):
        p = dict(params)
        for k, v in ch.items():
            if isinstance(v, str) and v.endswith("%"):
                p[k] = p[k] * (1 + float(v[:-1]) / 100)
            else:
                p[k] = v
        return p
    out = {"base": _summ(unit_economics(**base), base)}
    for name, ch in changes.items():
        params = apply(base, ch)
        out[name] = _summ(unit_economics(**params), params)
        if out[name]["profit_per_customer"] is not None and out["base"]["profit_per_customer"] is not None:
            out[name]["delta_profit_per_customer"] = round(out[name]["profit_per_customer"] - out["base"]["profit_per_customer"], 2)
    return out


def _summ(ue, params):
    return {"params": params, "profit_per_customer": ue.get("profit_per_customer"),
            "ltv_to_cac": ue.get("ltv_to_cac", {}).get("value"), "gross_margin": ue.get("gross_margin", {}).get("value"),
            "ok": ue.get("ok"), "error": ue.get("error")}


def campaign_summary(m: dict, gross_margin_rate: float | None = None) -> dict:
    """m: {impressions, clicks, spend, leads, conversions, revenue, visitors}. Computes everything available."""
    out = {
        "ctr": ctr(m.get("clicks"), m.get("impressions")),
        "cpc": cpc(m.get("spend"), m.get("clicks")),
        "cpm": cpm(m.get("spend"), m.get("impressions")),
        "cpl": cpl(m.get("spend"), m.get("leads")),
        "cpa": cpa(m.get("spend"), m.get("conversions")),
        "click_to_conversion": conversion_rate(m.get("conversions"), m.get("clicks") if m.get("visitors") is None else m.get("visitors")),
        "roas": roas(m.get("revenue"), m.get("spend")),
        "revenue_per_visitor": revenue_per_visitor(m.get("revenue"), m.get("visitors") or m.get("clicks")),
    }
    if gross_margin_rate is not None and _num(m.get("revenue")):
        out["breakeven_roas"] = breakeven_roas(gross_margin_rate)
        out["poas"] = poas(m["revenue"] * gross_margin_rate, m.get("spend"))
        if out["roas"]["ok"] and out["breakeven_roas"]["ok"]:
            out["profitable_on_first_purchase"] = out["roas"]["value"] >= out["breakeven_roas"]["value"]
    return out
