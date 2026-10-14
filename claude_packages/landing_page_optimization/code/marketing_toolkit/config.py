"""Configuration with sensible defaults. Override with a JSON file
(MKT_CONFIG env var or ./marketing_toolkit.config.json) or by passing a dict.
No credentials are ever read or stored here."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent

DEFAULTS: dict = {
    "db_path": str(REPO_ROOT / "data" / "marketing.db"),
    "export_dir": str(REPO_ROOT / "dist" / "claude_packages"),
    "export_max_bytes": 1_500_000,          # per task package (source + docs + knowledge)
    "export_knowledge_max_records": 200,
    # Offer scoring weights (normalised automatically)
    "offer_weights": {
        "target_customer": 1.0, "problem": 1.0, "outcome": 1.0, "value_proposition": 1.2,
        "differentiation": 1.0, "pricing": 1.0, "packaging": 0.6, "deliverables": 0.6,
        "time_to_value": 0.8, "risk_reversal": 0.8, "proof": 1.2, "urgency": 0.5,
        "friction": 0.7, "alternatives": 0.6, "economics": 1.2,
    },
    "offer_pass_score": 3.5,                 # 0-5 scale
    # Copy evaluation weights
    "copy_weights": {
        "audience_relevance": 1.0, "clarity": 1.2, "specificity": 1.0, "credibility": 1.0,
        "value_proposition": 1.2, "differentiation": 0.8, "emotional_relevance": 0.7,
        "proof": 1.0, "objection_coverage": 0.7, "readability": 0.8, "cta": 1.0,
        "offer_consistency": 1.0,
    },
    "copy_pass_score": 3.5,
    # Quality control
    "qc_reject_on": ["unsupported_claim", "fabricated_testimonial", "misleading_scarcity",
                     "unrealistic_promise", "policy_risk_high"],
    "qc_max_warnings": 4,
    "concept_similarity_threshold": 0.55,    # creative concepts more similar than this are "repeats"
    # Experiments
    "alpha": 0.05,
    "power": 0.8,
    "min_conversions_per_arm": 30,
    "min_visitors_per_arm": 300,
    # VoC
    "voc_cluster_threshold": 0.35,
    "voc_near_duplicate_threshold": 0.85,
}


def load_config(overrides: dict | None = None, path: str | None = None) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    p = path or os.environ.get("MKT_CONFIG")
    if not p and (REPO_ROOT / "marketing_toolkit.config.json").exists():
        p = str(REPO_ROOT / "marketing_toolkit.config.json")
    if p:
        _merge(cfg, json.loads(Path(p).read_text()))
    if overrides:
        _merge(cfg, overrides)
    return cfg


def _merge(base: dict, new: dict) -> None:
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
