# Returning results to the local system

When you produce findings worth keeping (customer insights, tested copy, ad concepts, objections heard,
campaign results, experiment outcomes, learnings), give the user a JSON file in this format:

```json
{"format": "marketing_toolkit.results.v1", "generated_by": "claude (chat)", "records": [ RECORD, ... ]}
```

RECORD fields (see schemas/record.json):
- kind (one of the record kinds), title, data (object)
- optional: product, audience, confidence (low/medium/high), basis (measured/observed/inferred/hypothesis), tags, sources, natural_key

Rules:
- Only include real data for `measured`/`observed` records (with sources). Everything you generated is `hypothesis`.
- Use `natural_key` when updating an existing record (e.g. the experiment_id) so the importer can detect conflicts.
- The user imports with:  `python -m marketing_toolkit import-results results.json`  (default: conflicts are reported, never overwritten;
  `--on-conflict version` keeps both versions with history; `--dry-run` previews).
