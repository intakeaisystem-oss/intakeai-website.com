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

## Creative angles
- **problem_led**: pain -> consequence -> solution -> CTA (stage: discovery; failure risk: Pain not felt strongly by this audience; reads as negative.)
- **product_demo**: task -> screen/hands-on demo -> result -> CTA (stage: discovery; failure risk: Demo too slow; value not visible in first 3 seconds.)
- **customer_proof**: real customer result -> how -> CTA (stage: consideration; failure risk: Proof not relatable to the viewer's situation.)
- **objection_handling**: objection -> truthful answer -> evidence -> CTA (stage: consideration; failure risk: Raises an objection the viewer didn't have.)
- **comparison**: status quo -> concrete difference -> who it's for -> CTA (stage: consideration; failure risk: Unfair/unverifiable comparison: legal and policy risk.)
- **founder_story**: founder's real problem -> insight -> product -> CTA (stage: discovery; failure risk: About the founder, not the viewer.)
- **outcome_visualization**: desired end state -> how it happens -> CTA (stage: discovery; failure risk: Outcome feels exaggerated or generic.)
- **educational**: useful lesson -> product as next step -> soft CTA (stage: discovery; failure risk: Educates without driving action; attracts non-buyers.)
- **unexpected_use_case**: surprising real use -> why it works -> CTA (stage: discovery; failure risk: Novelty without relevance to the core buyer.)
- **offer_led**: offer -> what's included -> risk reversal -> CTA (stage: conversion; failure risk: Discount-trained buyers; margin erosion.)

## Psychological dimensions (each needs evidence or is marked hypothesis)
- desires_outcomes: validate by Interview: 'What would have to be true for this to be a success for you?'
- problems_frustrations: validate by Interview: 'Tell me about the last time this went wrong.'
- emotional_motivation: validate by Interview follow-up: 'How did that make you feel?' and code answers.
- practical_motivation: validate by Survey: rank outcomes (time, money, quality, risk).
- purchase_triggers: validate by Switch interview: 'What happened that made you start looking?'
- urgency_timing: validate by Ask for timeline in discovery; compare time-to-purchase across segments.
- perceived_value: validate by Van Westendorp or willingness-to-pay interview questions.
- perceived_risk: validate by Ask 'What's the worst that could happen if you bought this?'
- trust_credibility: validate by Test proof placement (A/B) and ask what would make them confident.
- social_proof: validate by Attribution survey: 'How did you hear about us?'
- loss_aversion: validate by A/B test gain-framed vs loss-framed headline.
- cognitive_load: validate by 5-second test and task-completion usability test.
- decision_fatigue: validate by Track pricing-page dwell and plan-choice abandonment.
- switching_costs: validate by Ask current-solution users what stops them switching.
- status_identity: validate by Interview: 'Who else sees the result of this?'
- convenience_effort: validate by Measure time-to-first-value and step completion.
- price_sensitivity: validate by Price test on landing page (fake-door / plan anchoring) with approval.
- habits_alternatives: validate by Ask 'How do you handle this today?'
- objections_friction: validate by Log objections in sales calls; count by type.
- awareness_sophistication: validate by Ask how they describe the problem and which solutions they tried.
- stated_vs_observed: validate by Compare survey/interview statements with analytics or purchase data.

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

## Objection library
price, no_budget, timing, need_unclear, trust, authority, competitor, status_quo, switching_cost, complexity, send_info, commitment, results_doubt, security_compliance, feature_gap
Disqualifying poor-fit buyers is a valid outcome.
