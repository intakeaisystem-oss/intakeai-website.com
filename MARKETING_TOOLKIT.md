# Marketing, Sales, Advertising & Conversion Toolkit

`marketing_toolkit/` is a working Python package (standard library only, Python 3.9+). It makes Claude better at:

- customer psychology and research
- offers and sales copy
- ads and funnels
- metrics and experiments
- sales conversations

It persists what it learns, and it exports task-specific packages that you upload to a normal Claude conversation.

- **For normal Claude:** upload a package from `claude_packages/`. Start with its `MASTER_INSTRUCTIONS.md`.
- **For developers:** read on.

## Quick start
```bash
python3 -m unittest discover -s tests -t .          # run the test suite
python3 scripts/demo_end_to_end.py --reset          # acceptance demo on illustrative data (separate demo DB)
python3 -m marketing_toolkit --help                 # CLI
python3 scripts/build_claude_packages.py            # rebuild all packages for normal Claude -> claude_packages/
```
There's nothing to install. Your persistent store is `data/marketing.db` (gitignored). Change it with `--db` or `marketing_toolkit.config.json`.

## The 13 systems
| # | System | Module | Main entry points |
|---|--------|--------|-------------------|
| 1 | Customer psychology & buying behaviour | `psychology.py` | `build_profile()` |
| 2 | Voice-of-customer analyzer | `voc.py` | `analyze()`, `to_records()` |
| 3 | Offer engineering | `offer.py` | `score_offer()`, `generate_structures()`, `economics()` |
| 4 | Sales copy & persuasion | `copywriting.py` | `FRAMEWORKS`, `CHANNELS`, `build_draft()`, `evaluate_copy()` |
| 5 | Ad creative & campaigns | `ads.py` | `ANGLES`, `generate_concepts()`, `campaign_plan()`, `VariantRegistry` |
| 6 | Funnel & conversion optimisation | `funnel.py` | `diagnose_funnel()`, `audit_landing_html()`, `audit_file()`, `audit_onboarding()` |
| 7 | Sales conversations & objections | `sales.py` | `handle_objection()`, `qualify()`, `discovery_questions()`, `ObjectionLog` |
| 8 | Experiments & A/B testing | `experiments.py` | `analyze()`, `sample_size_per_arm()`, `ExperimentManager` |
| 9 | Analytics & unit economics | `metrics.py` | 25+ metric functions, `funnel()`, `unit_economics()`, `scenarios()`, `campaign_summary()` |
| 10 | Marketing memory & learning | `store.py` | `KnowledgeStore` (SQLite, history, dedupe, conflicts) |
| 11 | Reusable components | `components.py`, `templates/` | `render_landing()`, `TEMPLATES`, `ANALYTICS_EVENTS`, `LandingSections.jsx` |
| 12 | Evaluation & quality control | `qc.py` | `evaluate()`: approve / revise / reject |
| 13 | Normal-Claude import/export | `export.py` | `build_package()`, `export_knowledge()`, `import_results()` |

Shared pieces:
- `schemas.py`: record and input schemas, plus a validator
- `text.py`: NLP utilities
- `config.py`: defaults, weights and thresholds
- `cli.py`: the command-line interface

## Source structure
```
marketing_toolkit/
  __init__.py  __main__.py  cli.py  config.py  schemas.py  store.py  text.py
  voc.py  psychology.py  offer.py  copywriting.py  qc.py  ads.py  funnel.py
  metrics.py  experiments.py  sales.py  components.py  export.py
  templates/LandingSections.jsx  templates/landing.css
tests/                       97 unit, integration and CLI tests
scripts/demo_end_to_end.py   11 acceptance checks
scripts/build_claude_packages.py
examples/marketing/          ILLUSTRATIVE sample inputs (fictional)
claude_packages/             generated packages (dirs + .zip) for normal Claude
```

## How the pieces connect
```
reviews / interviews / tickets ─► voc.analyze ─► psychology.build_profile ─┐
                                                                           ▼
offer dict ─► offer.score_offer ─► copywriting.build_draft / evaluate_copy ─► qc.evaluate (gate)
                    │                         │
                    ▼                         ▼
             ads.generate_concepts ─► VariantRegistry ─► results ─► metrics / experiments.analyze
                    │
landing source ─► funnel.audit_landing_html      funnel numbers ─► funnel.diagnose_funnel
                    │
everything ─► store.KnowledgeStore ─► export.build_package(task) ─► normal Claude
                                   ◄─ export.import_results(results.json) ◄──┘
```

## Persistence and safe import
| Situation | What the store does |
|-----------|---------------------|
| Exact duplicate (same kind and content) | Not re-inserted (`duplicate`) |
| Same `natural_key`, different content | `ConflictError` by default, so it's never silently overwritten |
| `on_conflict="version"` | Keeps the old content in `record_history` and stores the new version |
| `on_conflict="skip"` | Keeps the existing record |
| An `update()` that changes nothing | No-op, with no history entry |
| Removing a record | Nothing is hard-deleted; `archive()` hides a record |

- **Import:** `python -m marketing_toolkit import-results results.json [--on-conflict version] [--dry-run]`.
- **Results format:** `marketing_toolkit.results.v1` (see `RETURN_RESULTS.md` in any package).

## Export for normal Claude
| Command | What it builds |
|---------|----------------|
| `python -m marketing_toolkit export paid_ads` | One task package |
| `python3 scripts/build_claude_packages.py` | All eight packages |

The tasks are `app_marketing`, `landing_page_optimization`, `paid_ads`, `sales_copy`, `sales_process`, `customer_research`, `conversion_analysis` and `marketing_full_toolkit`.

Each package contains:

| File or folder | Contents |
|----------------|----------|
| `MASTER_INSTRUCTIONS.md` | Tells Claude to check its tools first, the rules, and the workflow |
| `USAGE.md` | How to call each included module |
| `METHODOLOGY.md` | Definitions, generated from the code's own constants |
| `CAPABILITIES.json` | What's runnable Python, what's reference code, what needs a runtime, and what isn't included |
| `CONFIG.md` | Configuration defaults |
| `schemas/` | Input and record schemas |
| `code/` | The real source, with dependencies resolved and checked to import standalone |
| `examples/` | Real program output on illustrative inputs |
| `knowledge/` | Your store's relevant records, size-limited |
| `RETURN_RESULTS.md` + `results_template.json` | How to bring results back |
| `MANIFEST.json` | Files and SHA-1 hashes |

The builder also writes a `.zip` of the package.

## Configuration
These are in `config.py`. Override them with `marketing_toolkit.config.json`, `MKT_CONFIG=path`, or a `config` argument.

- Offer and copy criterion weights, and their pass thresholds
- QC reject codes and the maximum number of warnings
- The concept-similarity threshold
- Experiment alpha and power, and the minimum conversions and visitors per arm
- VoC clustering and dedupe thresholds
- Export size and record limits

## Implementation status
| Capability | Status |
|------------|--------|
| All 13 systems listed above | **Implemented and tested** (97 tests pass; 11/11 acceptance checks pass) |
| Exported packages import and run standalone (`python -I`) | **Tested** |
| Output is deterministic across Python hash seeds | **Tested** |
| Rule-based NLP (cue phrases, TF-IDF clustering) | **Implemented.** Transparent and deterministic, but less nuanced than an LLM. Outputs are labelled for human review |
| Landing-page audit | **HTML: implemented.** JSX/TSX/Vue/Svelte: heuristic. Static only (no rendering, speed or real-user data) |
| Platform policy checks | **Heuristic flags**, not an official review |
| Ad platform, analytics and CRM integrations | **Not implemented.** No credentials or accounts are used. Supply metrics as exported data |
| Semantic or embedding search over the store | **Not implemented.** Filters plus `LIKE` text search only |
| Persistent store inside a claude.ai chat | **Not possible.** The chat sandbox is temporary, so results return via JSON import |

## Rules the code enforces
- Proof, testimonials, guarantees and urgency count only when marked verified or real.
  - Unverified proof is dropped from rendered pages and drafts.
  - QC rejects fabricated testimonials, fake scarcity and unrealistic promises.
- Every insight carries `basis` (`observed`, `measured`, `inferred` or `hypothesis`) and `confidence`. Quotes are verbatim substrings of the input.
- Scores are labelled as heuristics, never as performance predictions. No recommendation claims a percentage lift.
- ROAS is reported as revenue. Profitability needs margin data (breakeven ROAS, POAS, contribution margin).
- Experiments refuse to name a winner on small samples, before the planned sample is reached, without practical significance, or when a guardrail is broken. Holm correction is applied for more than one variant.
- Nothing launches campaigns, spends money, contacts anyone or publishes anything. Plans list the approvals required.
