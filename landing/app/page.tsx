'use client'

import Image from 'next/image'

import HeroShowcase from '@/components/hero-showcase'
import IndustryTabs from '@/components/industry-tabs'
import { usePreferences } from '@/components/preferences-context'
import SiteShell from '@/components/site-shell'
import { BrandIcon } from '@/components/brand-icons'
import { MODULE_VISUAL_PLACEHOLDERS } from '@/content/module-placeholders'
import { copy } from '@/content/i18n'

const partnerNames = ['Meta', 'TikTok', 'Zalo', 'Facebook', 'Lazada', 'Instagram']
const pressNames = ['VnExpress Young', '24h', 'CafeF', 'Soha']

export default function HomePage() {
  const { lang } = usePreferences()
  const t = copy[lang]
  const home = t.homeContent

  return (
    <SiteShell>
      <section className="container py-10 md:py-14">
        <div className="hero-layout grid items-start gap-10 lg:grid-cols-2 lg:gap-12">
          <div className="min-w-0">
            <h1 className="hero-title animate-fade-up">
              {home.hero.titleLine1}
              <br />
              <span className="hero-title-accent">{home.hero.titleLine2}</span>
            </h1>
            <p className="animate-fade-up delay-1 mt-5 max-w-xl text-lg leading-8 text-slate-600">
              {home.hero.subtitle}
            </p>
            <div className="animate-fade-up delay-2 mt-8 flex flex-wrap gap-3">
              <a className="btn btn-secondary" href="/contact">{home.hero.ctaDemo}</a>
              <a className="btn btn-primary" href="/signup">{home.hero.ctaTrial}</a>
            </div>
          </div>
          <div className="animate-fade-up delay-2 min-w-0">
            <HeroShowcase content={home.hero.showcase} />
          </div>
        </div>
      </section>

      <section className="container py-12 md:py-16" id="platform">
        <h2 className="section-title text-center">
          {home.platform.titleLine1}
          <br />
          <span className="text-[var(--primary)]">{home.platform.titleLine2}</span>
        </h2>
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {home.platform.features.map(feature => (
            <article className="platform-card card p-6" key={feature.title}>
              <h3 className="text-lg font-semibold">{feature.title}</h3>
              <p className="mt-3 text-sm leading-7 text-slate-600">{feature.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="container py-12 md:py-16" id="modules">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <h2 className="section-title">{home.modules.title}</h2>
          <span className="module-badge">{home.modules.badge}</span>
        </div>
        <div className="space-y-10">
          {home.modules.items.map((module, index) => (
            <article
              className={`module-block card grid gap-6 p-6 md:grid-cols-2 md:p-8 ${index % 2 === 1 ? 'module-block-reverse' : ''}`}
              key={module.title}
            >
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">{module.subtitle}</p>
                <h3 className="mt-2 text-2xl font-bold">{module.title}</h3>
                <ul className="mt-5 space-y-4">
                  {module.points.map(point => (
                    <li key={point.title}>
                      <h4 className="font-semibold">{point.title}</h4>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{point.description}</p>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="module-visual" aria-hidden="true">
                <Image
                  alt=""
                  className="module-visual-img"
                  fill
                  sizes="(min-width: 768px) 42vw, 100vw"
                  src={MODULE_VISUAL_PLACEHOLDERS[index % MODULE_VISUAL_PLACEHOLDERS.length]}
                />
                <div className="module-visual-scrim" />
                <div className="module-visual-inner">
                  <span>{module.title}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <IndustryTabs content={home.industries} />

      <section className="container py-10 md:py-14">
        <h2 className="section-title text-center">{home.partners.title}</h2>
        <div className="partner-row mt-8">
          {partnerNames.map(name => (
            <span className="partner-pill partner-pill--brand" key={name}>
              <BrandIcon className="partner-pill-icon" name={name} size={22} />
              <span>{name}</span>
            </span>
          ))}
        </div>
      </section>

      <section className="container py-8 md:py-12">
        <h2 className="section-title text-center">{home.partners.pressTitle}</h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-sm text-slate-600">{home.partners.pressSubtitle}</p>
        <div className="press-row mt-8">
          {pressNames.map(name => (
            <span className="press-pill" key={name}>{name}</span>
          ))}
        </div>
      </section>

      <section className="container py-12 md:py-16" id="contact">
        <div className="contact-grid card grid gap-8 p-6 md:grid-cols-2 md:p-10">
          <div>
            <h2 className="section-title">{home.contact.title}</h2>
            <p className="mt-4 text-sm leading-7 text-slate-600">{home.contact.subtitle}</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <a className="btn btn-secondary" href="/contact">{home.contact.partner}</a>
              <a className="btn btn-primary" href="/signup">{home.contact.signup}</a>
            </div>
            <p className="mt-6 text-sm text-slate-600">{home.contact.tagline}</p>
          </div>
          <form className="contact-form space-y-4" onSubmit={e => e.preventDefault()}>
            <label className="form-field">
              <span>{home.contact.nameLabel}</span>
              <input required type="text" />
            </label>
            <label className="form-field">
              <span>{home.contact.phoneLabel}</span>
              <input required type="tel" />
            </label>
            <label className="form-field">
              <span>{home.contact.industryLabel}</span>
              <input required type="text" />
            </label>
            <button className="btn btn-primary w-full" type="submit">{home.contact.submit}</button>
          </form>
        </div>
      </section>

      <section className="container pb-20">
        <h2 className="section-title text-center">{home.faq.title}</h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-sm text-slate-600">{home.faq.subtitle}</p>
        <div className="mt-8 grid gap-3">
          {home.faq.items.map(item => (
            <details className="card p-5" key={item.q}>
              <summary className="cursor-pointer text-base font-semibold">{item.q}</summary>
              <p className="mt-3 text-sm leading-6 text-slate-600">{item.a}</p>
            </details>
          ))}
        </div>
      </section>
    </SiteShell>
  )
}


