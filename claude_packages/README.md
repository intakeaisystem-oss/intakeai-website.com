# Packages for normal Claude

Pick the package that matches the task, and upload its `.zip` (or the folder's files) to a Claude conversation or Project. Tell Claude to start with `MASTER_INSTRUCTIONS.md`.

| Package | Use it for |
|---------|-----------|
| `app_marketing` | Positioning, onboarding, activation, upgrade flows and app-store copy for an app |
| `landing_page_optimization` | Auditing and rewriting landing pages; conversion experiments |
| `paid_ads` | Ad concepts, variants, campaign plans and post-campaign analysis |
| `sales_copy` | Landing copy, emails, product descriptions and CTAs |
| `sales_process` | Qualification, discovery, objection handling and follow-up |
| `customer_research` | Turning reviews, interviews and tickets into evidence-tagged insight |
| `conversion_analysis` | Funnel metrics, unit economics and A/B test analysis |
| `marketing_full_toolkit` | Everything above |

Each package holds the real Python source (standard library only), instructions, schemas, examples and a knowledge export. The knowledge export is empty until you add data to your local store.

Rebuild after adding knowledge: `python3 scripts/build_claude_packages.py`. Bring new results back with `python -m marketing_toolkit import-results results.json`.
