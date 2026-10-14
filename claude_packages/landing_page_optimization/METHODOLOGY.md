# METHODOLOGY (generated from the code)

## Evidence basis
- measured: number from real campaign/analytics data
- observed: customer said/did it (verbatim, sourced)
- inferred: reasoned from observed evidence
- hypothesis: plausible, untested: validate before relying on it

## Awareness levels
unaware, problem_aware, solution_aware, product_aware, most_aware

## Funnel stages
discovery -> landing -> signup -> activation -> purchase -> retention -> referral

## Copy frameworks
- **pas** (Problem-Agitation-Solution), best for ['problem_aware']: problem -> agitation -> solution -> proof -> cta
- **aida** (Attention-Interest-Desire-Action), best for ['unaware', 'problem_aware']: attention -> interest -> desire -> action
- **bab** (Before-After-Bridge), best for ['problem_aware', 'solution_aware']: before -> after -> bridge -> cta
- **fab** (Feature-to-Benefit), best for ['product_aware']: feature -> advantage -> benefit -> cta
- **objection_led** (Objection-led), best for ['product_aware', 'solution_aware']: objection -> reframe -> proof -> cta
- **proof_led** (Proof-led), best for ['product_aware', 'most_aware']: proof -> outcome -> offer -> cta
- **comparison** (Comparison-led), best for ['solution_aware']: alternative -> difference -> who_for -> cta
- **story** (Story-led), best for ['unaware', 'problem_aware']: character -> conflict -> turning_point -> resolution -> cta
- **demonstration** (Demonstration-led), best for ['solution_aware', 'product_aware']: setup -> demo -> result -> cta
- **risk_reduction** (Risk-reduction), best for ['product_aware', 'most_aware']: risk -> reversal -> proof -> cta

## Channel length defaults (verify current platform limits)
- google_rsa_headline: {'max_chars': 30}
- google_rsa_description: {'max_chars': 90}
- meta_primary_text: {'soft_max_chars': 125}
- meta_headline: {'soft_max_chars': 40}
- tiktok_ad_text: {'max_chars': 100}
- youtube_script_15s: {'max_words': 40}
- youtube_script_30s: {'max_words': 80}
- app_store_title: {'max_chars': 30}
- app_store_subtitle: {'max_chars': 30}
- app_store_promo: {'max_chars': 170}
- email_subject: {'soft_max_chars': 60}
- sms: {'max_chars': 160}
- x_post: {'max_chars': 280}
- linkedin_post: {'soft_max_chars': 1300}
- landing_headline: {'soft_max_words': 14}
- cold_email: {'soft_max_words': 125}
- push_notification: {'soft_max_chars': 110}
- cta_button: {'soft_max_words': 5}

## Offer criteria
target_customer, problem, outcome, value_proposition, differentiation, pricing, packaging, deliverables, time_to_value, risk_reversal, proof, urgency, friction, alternatives, economics

## Metric formulas
- CTR = clicks/impressions; CPC = spend/clicks; CPL = spend/leads; CPA = spend/conversions
- CAC = all acquisition costs / new customers; ROAS = revenue/spend (revenue, not profit)
- Breakeven ROAS = 1/gross margin; POAS = gross profit/spend
- LTV (gross profit) = ARPU x GM / churn; Payback = CAC / monthly GP per customer

## Experiment rules
- Two-proportion z-test, Wilson CIs, Holm correction for >1 variant
- No winner below 30 conversions or 300 visitors per arm, or before planned sample
- Practical significance: lift must reach the minimum detectable effect
