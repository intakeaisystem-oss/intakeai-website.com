# USAGE: sales_process

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

## sales
```python
from marketing_toolkit import sales
sales.handle_objection("it's too expensive", {'price': 99})
sales.qualify({'problem': 2, 'budget': 1, 'authority': None, 'timing': 1, 'fit': 2})
sales.discovery_questions('b2b_services')
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