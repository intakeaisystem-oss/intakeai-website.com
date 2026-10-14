# The 10 Agents

Every agent writes a result file in the format in `protocol/OUTPUT_SCHEMA.md`, which contains:

- task ID, agent and role, research question
- findings, source URLs and evidence, verified facts
- estimates and assumptions
- confidence, contradictory evidence, limitations
- next steps, status, timestamp

The full instructions are in `.claude/agents/<name>.md`.

| # | Agent (file name) | Responsibility | Main inputs | Key outputs | Tools |
|---|-------------------|----------------|-------------|-------------|-------|
| 1 | Market Intelligence (`market-intelligence`) | Opportunities, emerging niches, market gaps, trends, underserved customers, online and offline | Objective, constraints, prior research | Candidates table (OPP IDs, customer group, economic buyer, signals, screen score), discarded ideas, counts | Web, read, write |
| 2 | Paying Customer Evidence (`paying-customer-evidence`) | Proof of existing spending, prices, contracts, procurement, paying competitor customers, expensive problems | Candidates | Spending-evidence rating per candidate, observed prices with dates, cost-of-problem evidence, budget owner | Web, read, write |
| 3 | Sales & Buyer Psychology (`sales-psychology`) | Buying decisions, triggers, objections, trust, qualification, negotiation, sales conversations. Uses **your** psychology, persuasion and 48 Laws notes, with an ethics filter | Candidates, buyers, knowledge note paths | Buyer decision profiles, "Knowledge applied" table citing your notes | Read, web, write |
| 4 | Marketing & Distribution (`marketing-distribution`) | Channels: SEO, content, outbound, partnerships, ads, directories, associations, offline | Candidates, competitor info | Channel map with scores, first-10-customers plan (needs approval to execute) | Web, read, write |
| 5 | Unit Economics (`unit-economics`) | Pricing, margins, startup costs, CAC, retention, LTV, cash flow, profit scenarios | Evidence, competitor and channel results | Inputs table (cited or assumed), 3 scenarios, sensitivity thresholds, verdict | Read, web, write |
| 6 | Competitor Intelligence (`competitor-intelligence`) | Competitors and alternatives, offers, pricing, positioning, review-based weaknesses, moats, differentiation | Candidates | Competitor matrix, market structure, differentiation options | Web, read, write |
| 7 | AI Tools & Automation (`ai-tools-automation`) | Tools, APIs, frameworks and workflows for running the business or improving this system, verified against official docs | Candidate ops or the research pipeline | Automation map (proven/plausible/speculative), minimal stack | Web, read, write |
| 8 | Knowledge & Memory (`knowledge-memory`) | Maintains the Obsidian brain: retrieval, dedupe, provenance, filing, indexes | Objective (retrieve) or job folder (file) | Prior-research table, recommended notes per agent, duplicate verdict, records written | Read, Grep, Glob, Write, Edit (no web) |
| 9 | Skeptic & Risk (`skeptic-risk`) | Challenges claims, re-checks sources, finds contradictions, pre-mortems, legal and operational risks | Selected important claims, all task files | Claim verdicts, cross-agent contradictions, pre-mortems, risk register, missing evidence | Web, read, write |
| 10 | Chief Intelligence & Orchestration (`research` skill + `chief-orchestrator`) | Delegates, tracks, retries, resumes (skill); merges, resolves contradictions, ranks, reports (agent) | Objective; then the job folder | job.md checkpoint, ranking with weighted rubric, `report.md` | Skill: all session tools; agent: Read, Grep, Glob, Write |

## Ranking rubric (chief-orchestrator)
| Criterion | Weight |
|-----------|--------|
| Spending evidence | 25% |
| Problem intensity | 15% |
| Unit economics | 20% |
| Reachability | 15% |
| Competitive opening | 10% |
| Fit with your constraints | 5% |
| Risk (inverse) | 10% |

Skeptic verdicts change how findings count:
- `unsupported` and `contradicted` findings are excluded.
- `weak`, `overstated` and `unverifiable` findings count at half weight.
