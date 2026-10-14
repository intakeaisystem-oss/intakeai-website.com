# USAGE: customer_research

```python
import sys; sys.path.insert(0, 'code')
```

## psychology
```python
from marketing_toolkit import psychology
profile = psychology.build_profile(product, 'audience', documents)
profile['messaging_implications']
```

## voc
```python
from marketing_toolkit import voc
res = voc.analyze(documents, competitors=['CompetitorX'])
res['categories']['objection']['themes'][0]['quotes']
```

All functions validate inputs against `schemas/` and return plain dicts (JSON-serialisable).