---
type: report
job_id: JOB-20261014-restaurant-b2b-services
created: 2026-10-14
research_mode: live
execution: parallel
example: true   # ILLUSTRATIVE — fictional data
---
# Report: recurring B2B services for US restaurants (ILLUSTRATIVE)

> Mode: **live**. Execution: **parallel** (batches of 4). Tasks: 10 complete, 1 partial, 0 failed.

## Bottom line
Of 6 screened candidates, 2 meet the evidence-supported bar. Grease-trap compliance servicing ranks first: regulation forces spending, and there are published prices. Its economics depend on route density, which is untested. Nothing here is validated by customer conversations yet.

## Counts
| Ideas generated | Distinct opportunities | Candidates screened | Deep investigations | Evidence-supported |
|---|---|---|---|---|
| 14 | 9 | 6 | 0 | 2 |

## Ranking
| Rank | Opportunity | Weighted score | Evidence strength | Decision | Why |
|------|-------------|----------------|-------------------|----------|-----|
| 1 | [[OPP-example-grease-trap-compliance]] | 3.7 | strong | pursue-deeper | Mandated spending (F1, F2); fragmented local providers |
| 2 | [[OPP-example-hood-cleaning-scheduling]] | 3.1 | moderate | watch | Real pain (F3); spending evidence from 1 source only |
| 3 | [[OPP-example-menu-photo-subscription]] | 2.4 | weak | reject | No spending evidence; Skeptic: price claim `unsupported` |

## Top candidates
### 1. [[OPP-example-grease-trap-compliance]]
- **Evidence:** ordinance [[SRC-0e1a2b3c]]; published price [[SRC-4d5e6f70]].
- **Economics (estimate):** base case break-even at ~N accounts (TASK-08). Fails if route density falls below M stops per day.
- **Main risks:** waste-hauling licence requirements (TASK-09); incumbent price cuts.
- **Skeptic's strongest challenge:** enforcement varies, so urgency may be low outside inspected areas.

## Contradictions & open questions
- TASK-04 and TASK-03 price points differ by 30%. Unresolved, because they come from different metros.

## Next steps — research
1. Run a deep job on OPP-example-grease-trap-compliance across 3 metros.
2. Check licensing requirements with official state sources.

## Next steps — require human approval
- Interview 5 restaurant owners.
- Get a quote from a licensed hauler.

## Appendix
Task files: `tasks/TASK-01…TASK-11`. Sources: the 23 records in `Sources/`.
