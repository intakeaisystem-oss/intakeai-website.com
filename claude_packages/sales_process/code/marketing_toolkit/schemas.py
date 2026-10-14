"""Schemas for every record type plus a small JSON-Schema-subset validator.

Supported keywords: type, required, properties, additionalProperties (bool),
enum, minimum, maximum, minLength, maxLength, pattern, items, minItems.
The schemas are also exported as JSON for normal Claude (see export.py).
"""

from __future__ import annotations

import re

CONFIDENCE = ["low", "medium", "high"]
# observed  = customer said/did it (verbatim quote, logged behaviour)
# measured  = a number from real campaign/analytics data
# inferred  = reasoned from observed evidence
# hypothesis= plausible, untested
BASIS = ["observed", "measured", "inferred", "hypothesis"]
AWARENESS = ["unaware", "problem_aware", "solution_aware", "product_aware", "most_aware"]
FUNNEL_STAGES = ["discovery", "landing", "signup", "activation", "purchase", "retention", "referral"]
RECORD_KINDS = [
    "customer_insight", "voc_finding", "offer", "copy_asset", "ad_concept", "ad_variant",
    "campaign_hypothesis", "objection", "funnel_audit", "experiment", "campaign_result",
    "approach", "source", "customer_profile",
]


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


_TYPES = {
    "string": str, "integer": int, "number": (int, float), "boolean": bool,
    "object": dict, "array": list, "null": type(None),
}


def _check(value, schema: dict, path: str, errors: list[str]) -> None:
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        ok = False
        for name in types:
            py = _TYPES[name]
            if name in ("integer", "number") and isinstance(value, bool):
                continue
            if isinstance(value, py):
                ok = True
                break
        if not ok:
            errors.append(f"{path or '$'}: expected {t}, got {type(value).__name__}")
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path or '$'}: {value!r} not in {schema['enum']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(value):
                _check(item, schema["items"], f"{path}[{i}]", errors)
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}.{req}: required" if path else f"{req}: required")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                _check(v, props[k], f"{path}.{k}" if path else k, errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{k}: unexpected property" if path else f"{k}: unexpected property")


def validate(value, schema: dict, raise_on_error: bool = True) -> list[str]:
    errors: list[str] = []
    _check(value, schema, "", errors)
    if errors and raise_on_error:
        raise ValidationError(errors)
    return errors


# ------------------------------------------------------------------ building blocks
S = {"type": "string"}
NUM = {"type": "number"}
NNUM = {"type": ["number", "null"]}
STRS = {"type": "array", "items": S}
CONF = {"type": "string", "enum": CONFIDENCE}

EVIDENCE_ITEM = {
    "type": "object",
    "required": ["basis"],
    "properties": {
        "basis": {"type": "string", "enum": BASIS},
        "quote": S,                       # verbatim customer language only
        "source_ref": S,                  # document id / URL / file:line
        "note": S,
        "count": {"type": "integer", "minimum": 0},
    },
}

INSIGHT = {
    "type": "object",
    "required": ["statement", "basis", "confidence"],
    "properties": {
        "statement": {"type": "string", "minLength": 3},
        "basis": {"type": "string", "enum": BASIS},
        "confidence": CONF,
        "evidence": {"type": "array", "items": EVIDENCE_ITEM},
        "validate_by": S,
    },
}

# ------------------------------------------------------------------ record envelope
RECORD = {
    "type": "object",
    "required": ["kind", "title", "data"],
    "properties": {
        "id": S,
        "kind": {"type": "string", "enum": RECORD_KINDS},
        "title": {"type": "string", "minLength": 2, "maxLength": 300},
        "product": S,
        "audience": S,
        "confidence": CONF,
        "basis": {"type": "string", "enum": BASIS},
        "tags": STRS,
        "sources": STRS,
        "status": S,
        "data": {"type": "object"},
        "natural_key": S,
    },
    "additionalProperties": False,
}

# ------------------------------------------------------------------ inputs
VOC_DOCUMENT = {
    "type": "object",
    "required": ["text"],
    "properties": {
        "id": S, "text": {"type": "string", "minLength": 1},
        "source_type": {"type": "string", "enum": [
            "review", "testimonial", "interview", "survey", "support_ticket", "sales_call",
            "feedback", "forum", "competitor_review", "product_feedback", "churn_reason", "other"]},
        "source_ref": S, "rating": NNUM, "date": S, "about": S,
        "quote_permitted": {"type": "boolean"},
    },
}

OFFER = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": S, "target_customer": S, "problem": S, "desired_outcome": S,
        "value_proposition": S, "differentiation": S,
        "price": NNUM, "currency": S, "billing": {"type": "string", "enum": [
            "one_time", "monthly", "annual", "usage", "retainer", "per_seat", "free", "other"]},
        "packaging": S, "deliverables": STRS, "time_to_value_days": NNUM,
        "risk_reversal": S, "guarantee_terms_verified": {"type": "boolean"},
        "proof": {"type": "array", "items": {"type": "object", "required": ["type", "verified"], "properties": {
            "type": {"type": "string", "enum": ["testimonial", "case_study", "metric", "review_rating",
                                                "logo", "certification", "demo", "data", "media"]},
            "detail": S, "verified": {"type": "boolean"}, "source_ref": S}}},
        "bonuses": STRS, "implementation_effort": {"type": "string", "enum": ["none", "low", "medium", "high"]},
        "urgency_reason": S, "urgency_is_real": {"type": "boolean"},
        "alternatives": STRS, "fulfillment_cost": NNUM, "acquisition_cost_estimate": NNUM,
        "expected_purchases_per_customer": NNUM,
    },
}

COPY_INPUT = {
    "type": "object",
    "required": ["text"],
    "properties": {
        "text": {"type": "string", "minLength": 1},
        "channel": S, "audience": S, "awareness": {"type": "string", "enum": AWARENESS},
        "offer": OFFER, "evidence_ids": STRS, "audience_terms": STRS,
        "known_objections": STRS, "brand_banned_words": STRS,
    },
}

EXPERIMENT = {
    "type": "object",
    "required": ["hypothesis", "funnel_stage", "control", "variant", "primary_metric"],
    "properties": {
        "experiment_id": S, "hypothesis": {"type": "string", "minLength": 10},
        "target_audience": S, "funnel_stage": {"type": "string", "enum": FUNNEL_STAGES},
        "category": {"type": "string", "enum": [
            "headline", "offer", "pricing_presentation", "ad_hook", "creative_concept", "cta",
            "landing_structure", "signup_flow", "onboarding", "email_sequence", "audience_segment", "other"]},
        "control": S, "variant": S, "variants": STRS,
        "primary_metric": S, "guardrail_metrics": STRS, "required_data": STRS,
        "start_date": S, "end_date": S,
        "baseline_rate": NNUM, "minimum_detectable_effect": NNUM,
        "status": {"type": "string", "enum": ["draft", "running", "completed", "stopped", "inconclusive"]},
    },
}

FUNNEL_INPUT = {
    "type": "object",
    "required": ["stages"],
    "properties": {
        "stages": {"type": "array", "minItems": 2, "items": {
            "type": "object", "required": ["name", "count"],
            "properties": {"name": S, "count": {"type": "number", "minimum": 0},
                           "message": S, "cta": S}}},
        "traffic_source": S, "offer": OFFER,
    },
}

CAMPAIGN_RESULT = {
    "type": "object",
    "required": ["title", "metrics"],
    "properties": {
        "title": S, "platform": S, "variant_id": S, "experiment_id": S, "product": S,
        "audience": S, "start_date": S, "end_date": S,
        "metrics": {"type": "object", "properties": {
            "impressions": NNUM, "clicks": NNUM, "spend": NNUM, "leads": NNUM,
            "conversions": NNUM, "revenue": NNUM, "visitors": NNUM}},
        "data_source": {"type": "string", "enum": ["platform_export", "analytics", "manual", "crm", "other"]},
        "notes": S,
    },
}

IMPORT_BUNDLE = {
    "type": "object",
    "required": ["format", "records"],
    "properties": {
        "format": {"type": "string", "enum": ["marketing_toolkit.results.v1"]},
        "generated_by": S,
        "records": {"type": "array", "items": RECORD},
    },
}

ALL_SCHEMAS = {
    "record": RECORD, "insight": INSIGHT, "evidence_item": EVIDENCE_ITEM,
    "voc_document": VOC_DOCUMENT, "offer": OFFER, "copy_input": COPY_INPUT,
    "experiment": EXPERIMENT, "funnel_input": FUNNEL_INPUT, "campaign_result": CAMPAIGN_RESULT,
    "import_bundle": IMPORT_BUNDLE,
}
