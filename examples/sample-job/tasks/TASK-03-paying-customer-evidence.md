---
type: task-result
task_id: TASK-03-paying-customer-evidence
job_id: JOB-20261014-restaurant-b2b-services
agent: paying-customer-evidence
role: Paying Customer Evidence Agent
research_question: "For each candidate, is there evidence US restaurants already pay for this service, at what prices?"
status: complete
confidence: medium
mode: live
timestamp: 2026-10-14T15:18:00Z
depends_on: [TASK-02-market-intelligence]
sources: [SRC-0e1a2b3c, SRC-4d5e6f70, SRC-8a9b0c1d]
internal_notes: []
candidates: [OPP-example-grease-trap-compliance, OPP-example-hood-cleaning-scheduling]
example: true   # ILLUSTRATIVE — fictional data
---
# TASK-03-paying-customer-evidence — Spending evidence (ILLUSTRATIVE)

## Research question
For each candidate, is there evidence that US restaurants already pay for this service, and at what prices?

## Summary
Grease-trap compliance servicing shows direct spending evidence: published service prices from two providers and a municipal ordinance requiring regular pumping. Hood-cleaning coordination shows a customer problem but only one pricing source. (Fictional example.)

## Findings
| ID | Claim | Evidence category | Source(s) | Confidence | Candidate |
|----|-------|-------------------|-----------|------------|-----------|
| F1 | Example City requires food-service grease traps to be pumped at a set interval | direct-commercial | SRC-0e1a2b3c | high | OPP-example-grease-trap-compliance |
| F2 | Provider A publishes a per-service price of $X for small traps | customer-spending | SRC-4d5e6f70 | medium | OPP-example-grease-trap-compliance |
| F3 | Owners complain about missed hood-cleaning appointments | customer-problem | SRC-8a9b0c1d | low | OPP-example-hood-cleaning-scheduling |

## Verified facts
- Example City ordinance §12 sets a pumping interval for grease traps. [SRC-0e1a2b3c]

## Estimates and assumptions
- **Estimate:** a typical restaurant needs 4–12 services per year, based on the F1 interval range. Method: the ordinance interval applied to trap sizes.
- **Assumption:** owners would outsource compliance tracking. Untested.

## Contradictory evidence
- One forum thread says many restaurants ignore the ordinance unless inspected (SRC-8a9b0c1d). This weakens urgency.

## Limitations
- Provider B's pricing page returned an error and was not accessed.
- Pricing is from one metro area only.

## Recommended next steps
1. Check ordinances in 3 more metros.
2. Collect 3 more published price points.
3. (Requires approval) Interview 5 restaurant owners.

## Sources
| Source ID | Title | URL | Publisher | Date | Accessed | Supports |
|-----------|-------|-----|-----------|------|----------|----------|
| SRC-0e1a2b3c | Example City FOG ordinance | https://example.com/ordinance | Example City | 2025-03 | yes | F1 |
| SRC-4d5e6f70 | Provider A pricing | https://example.com/pricing | Provider A | unknown | yes | F2 |
| SRC-8a9b0c1d | Restaurant owners forum thread | https://example.com/forum/123 | Example Forum | 2026-01 | yes | F3, contradiction |

## Search log
- "grease trap pumping ordinance <city>" → SRC-0e1a2b3c
- "grease trap service price" → SRC-4d5e6f70 (Provider B: error)
