# USAGE: paid_ads

```python
import sys; sys.path.insert(0, 'code')
```

## ads
```python
from marketing_toolkit import ads
ads.generate_concepts(brief)
ads.campaign_plan(brief, budget={'daily': 50, 'days': 14, 'assumed_cpc': 1.5, 'assumed_cvr': 0.03})
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

## psychology
```python
from marketing_toolkit import psychology
profile = psychology.build_profile(product, 'audience', documents)
profile['messaging_implications']
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

## voc
```python
from marketing_toolkit import voc
res = voc.analyze(documents, competitors=['CompetitorX'])
res['categories']['objection']['themes'][0]['quotes']
```

All functions validate inputs against `schemas/` and return plain dicts (JSON-serialisable).