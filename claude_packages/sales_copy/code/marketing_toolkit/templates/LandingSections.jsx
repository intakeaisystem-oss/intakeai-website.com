// Brand-neutral, conversion-focused landing sections for React apps.
// Pair with landing.css (CSS variables for theming). No dependencies.
// Rules baked in: one primary CTA per section, proof renders only when verified,
// pricing highlights a recommended plan, forms stay short, analytics hooks via onEvent.

import React from "react";

const track = (onEvent, name, props) => onEvent && onEvent({ event: name, properties: props });

export function Hero({ headline, subheadline, ctaText, ctaHref = "#signup", note, onEvent }) {
  return (
    <section id="hero" className="mk-section">
      <div className="mk-wrap">
        <h1>{headline}</h1>
        {subheadline && <p className="mk-sub">{subheadline}</p>}
        <a className="mk-cta" href={ctaHref} onClick={() => track(onEvent, "cta_click", { page: "landing", cta: "hero" })}>
          {ctaText}
        </a>
        {note && <p className="mk-note">{note}</p>}
      </div>
    </section>
  );
}

export function Problem({ heading, points = [] }) {
  return (
    <section id="problem" className="mk-section">
      <div className="mk-wrap">
        <h2>{heading}</h2>
        <ul>{points.map((p, i) => <li key={i}>{p}</li>)}</ul>
      </div>
    </section>
  );
}

export function HowItWorks({ heading = "How it works", steps = [] }) {
  return (
    <section id="how-it-works" className="mk-section">
      <div className="mk-wrap">
        <h2>{heading}</h2>
        <ol className="mk-grid">
          {steps.map((s, i) => (
            <li className="mk-card" key={i}><strong>{s.title}</strong><p>{s.text}</p></li>
          ))}
        </ol>
      </div>
    </section>
  );
}

// items: [{ quote | stat, attribution, verified: true, sourceRef }]
export function Proof({ heading = "What customers say", items = [] }) {
  const verified = items.filter((i) => i.verified === true);
  if (!verified.length) return null; // never render unverified proof
  return (
    <section id="proof" className="mk-section">
      <div className="mk-wrap">
        <h2>{heading}</h2>
        <div className="mk-grid">
          {verified.map((i, k) => (
            <figure className="mk-card" key={k}>
              {i.quote ? <blockquote>{i.quote}</blockquote> : <p className="mk-price">{i.stat}</p>}
              <figcaption className="mk-note">{i.attribution}</figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

// plans: [{ name, price, period, features: [], ctaText, ctaHref, featured }]
export function Pricing({ heading = "Pricing", plans = [], note, onEvent }) {
  return (
    <section id="pricing" className="mk-section">
      <div className="mk-wrap">
        <h2>{heading}</h2>
        <div className="mk-grid">
          {plans.map((p) => (
            <div className={`mk-card mk-plan${p.featured ? " mk-featured" : ""}`} key={p.name}>
              {p.featured && <p className="mk-note">Recommended</p>}
              <h3>{p.name}</h3>
              <p className="mk-price">{p.price}<span className="mk-note">{p.period}</span></p>
              <ul>{(p.features || []).map((f, i) => <li key={i}>{f}</li>)}</ul>
              <a className="mk-cta" href={p.ctaHref || "#signup"}
                 onClick={() => track(onEvent, "cta_click", { page: "landing", cta: `pricing-${p.name}` })}>
                {p.ctaText || "Choose"}
              </a>
            </div>
          ))}
        </div>
        {note && <p className="mk-note">{note}</p>}
      </div>
    </section>
  );
}

export function FAQ({ heading = "Questions", items = [] }) {
  return (
    <section id="faq" className="mk-section">
      <div className="mk-wrap">
        <h2>{heading}</h2>
        {items.map((i, k) => (
          <details key={k}><summary>{i.q}</summary><p>{i.a}</p></details>
        ))}
      </div>
    </section>
  );
}

// fields default to email only; keep it short.
export function LeadForm({ heading = "Get started", fields = [{ name: "email", label: "Email", type: "email", required: true }],
                           submitText, privacyNote = "We only use your details to respond. No spam.", onSubmit, onEvent }) {
  const handle = (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    track(onEvent, "lead_submitted", { form: "lead", page: "landing", fields_count: fields.length });
    onSubmit && onSubmit(data);
  };
  return (
    <section id="signup" className="mk-section">
      <div className="mk-wrap">
        <h2>{heading}</h2>
        <form className="mk-form" onSubmit={handle}>
          {fields.map((f) => (
            <React.Fragment key={f.name}>
              <label htmlFor={`f-${f.name}`}>{f.label || f.name}</label>
              <input id={`f-${f.name}`} name={f.name} type={f.type || "text"} required={!!f.required} autoComplete={f.autocomplete || f.name} />
            </React.Fragment>
          ))}
          <button className="mk-cta" type="submit">{submitText}</button>
          <p className="mk-note">{privacyNote}</p>
        </form>
      </div>
    </section>
  );
}

// Contextual upgrade prompt: show when the user hits a limit or touches a premium feature.
export function UpgradePrompt({ trigger, usageFact, plan, benefit, ctaText = "Upgrade", onUpgrade, onDismiss, onEvent }) {
  React.useEffect(() => { track(onEvent, "upgrade_prompt_shown", { trigger, plan }); }, [trigger, plan]);
  return (
    <div role="dialog" aria-label="Upgrade" className="mk-card mk-upgrade">
      <p>You've {usageFact}. <strong>{plan}</strong> lets you {benefit}.</p>
      <button className="mk-cta" onClick={() => { track(onEvent, "upgrade_prompt_clicked", { trigger, plan }); onUpgrade && onUpgrade(); }}>
        {ctaText}
      </button>{" "}
      <button className="mk-link" onClick={onDismiss}>Not now</button>
    </div>
  );
}

// Onboarding checklist: shows progress toward the activation event.
export function OnboardingChecklist({ steps = [], onEvent }) {
  const done = steps.filter((s) => s.done).length;
  return (
    <div className="mk-card" aria-label="Getting started">
      <p className="mk-note">{done} of {steps.length} done</p>
      <ol>
        {steps.map((s, i) => (
          <li key={i} style={{ textDecoration: s.done ? "line-through" : "none" }}>
            {s.href ? <a href={s.href} onClick={() => track(onEvent, "cta_click", { page: "onboarding", cta: s.label })}>{s.label}</a> : s.label}
          </li>
        ))}
      </ol>
    </div>
  );
}
