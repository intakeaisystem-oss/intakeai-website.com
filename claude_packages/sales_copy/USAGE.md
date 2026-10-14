# USAGE: sales_copy

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

## voc
```python
from marketing_toolkit import voc
res = voc.analyze(documents, competitors=['CompetitorX'])
res['categories']['objection']['themes'][0]['quotes']
```

All functions validate inputs against `schemas/` and return plain dicts (JSON-serialisable).