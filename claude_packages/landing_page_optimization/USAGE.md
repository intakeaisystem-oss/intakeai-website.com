# USAGE: landing_page_optimization

```python
import sys; sys.path.insert(0, 'code')
```

## components
```python
from marketing_toolkit import components as c
page = c.render_landing(cfg)['html']
c.render_template('email_abandoned_cart', values)
c.validate_event({'event': 'purchase', 'properties': {...}})
# React: code/marketing_toolkit/templates/LandingSections.jsx
```

## copywriting
```python
from marketing_toolkit import copywriting as cw
cw.recommend_framework('problem_aware', 'landing_page')
cw.build_draft('pas', brief)
cw.evaluate_copy({'text': draft, 'offer': offer_dict, 'channel': 'meta_primary_text', 'kind': 'ad'})
```

## experiments
```python
from marketing_toolkit import experiments as ex
ex.sample_size_per_arm(0.04, 0.1)
ex.analyze({'control': {'n': 4000, 'conversions': 160}, 'B': {'n': 4000, 'conversions': 200}}, 'control', mde_relative=0.1)
```

## funnel
```python
from marketing_toolkit import funnel
funnel.audit_landing_html(html_string, 'html', {'offer': offer_dict})
funnel.audit_file('src/pages/Landing.jsx')
funnel.diagnose_funnel({'stages': [...]})
funnel.audit_onboarding(spec)
```

## metrics
```python
from marketing_toolkit import metrics as m
m.roas(revenue, spend); m.breakeven_roas(0.6); m.ltv(49, 0.8, 0.04)
m.campaign_summary({'impressions':..., 'clicks':..., 'spend':..., 'conversions':..., 'revenue':...}, gross_margin_rate=0.6)
```

## offer
```python
from marketing_toolkit import offer
score = offer.score_offer(offer_dict)
score['top_improvements']
offer.generate_structures(offer_dict)
```

## qc
```python
from marketing_toolkit import qc
qc.evaluate(text, {'kind': 'ad', 'substantiated_claims': [...], 'landing_text': page_text})
```

## store
```python
from marketing_toolkit.store import KnowledgeStore
s = KnowledgeStore('marketing.db')  # or ':memory:'
s.add(record); s.find(kind='customer_insight')
```

All functions validate inputs against `schemas/` and return plain dicts (JSON-serialisable).