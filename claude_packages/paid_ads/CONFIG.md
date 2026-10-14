# Configuration defaults

Override by passing a dict to functions that accept `config`, or a JSON file via MKT_CONFIG.

```json
{
  "export_max_bytes": 1500000,
  "export_knowledge_max_records": 200,
  "offer_weights": {
    "target_customer": 1.0,
    "problem": 1.0,
    "outcome": 1.0,
    "value_proposition": 1.2,
    "differentiation": 1.0,
    "pricing": 1.0,
    "packaging": 0.6,
    "deliverables": 0.6,
    "time_to_value": 0.8,
    "risk_reversal": 0.8,
    "proof": 1.2,
    "urgency": 0.5,
    "friction": 0.7,
    "alternatives": 0.6,
    "economics": 1.2
  },
  "offer_pass_score": 3.5,
  "copy_weights": {
    "audience_relevance": 1.0,
    "clarity": 1.2,
    "specificity": 1.0,
    "credibility": 1.0,
    "value_proposition": 1.2,
    "differentiation": 0.8,
    "emotional_relevance": 0.7,
    "proof": 1.0,
    "objection_coverage": 0.7,
    "readability": 0.8,
    "cta": 1.0,
    "offer_consistency": 1.0
  },
  "copy_pass_score": 3.5,
  "qc_reject_on": [
    "unsupported_claim",
    "fabricated_testimonial",
    "misleading_scarcity",
    "unrealistic_promise",
    "policy_risk_high"
  ],
  "qc_max_warnings": 4,
  "concept_similarity_threshold": 0.55,
  "alpha": 0.05,
  "power": 0.8,
  "min_conversions_per_arm": 30,
  "min_visitors_per_arm": 300,
  "voc_cluster_threshold": 0.35,
  "voc_near_duplicate_threshold": 0.85
}
```
