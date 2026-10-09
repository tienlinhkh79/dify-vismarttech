'use client'

import { usePreferences } from '@/components/preferences-context'
import SiteShell from '@/components/site-shell'
import { planCards, siteContent } from '@/content/site'

export default function PricingPage() {
  const { lang } = usePreferences()
  const title = lang === 'vi' ? 'Bảng gói dịch vụ theo quy mô sử dụng' : 'Pricing plans by organization scale'
  const desc = lang === 'vi'
    ? 'Cấu trúc gói được ánh xạ từ giới hạn vận hành trong hệ thống để dễ nâng cấp theo từng giai đoạn tăng trưởng.'
    : 'Plans are aligned with operational limits in the platform so teams can scale step by step.'
  const ctaTitle = lang === 'vi' ? 'Cần tư vấn gói phù hợp?' : 'Need help choosing the right plan?'
  const ctaPrimary = lang === 'vi' ? 'Tạo workspace' : 'Create Workspace'
  const ctaSecondary = lang === 'vi' ? 'Liên hệ tư vấn' : 'Contact Sales'
  const note = lang === 'vi'
    ? `Bảng giá chi tiết sẽ được đội ngũ ${siteContent.company} tư vấn theo nhu cầu triển khai.`
    : `Detailed pricing can be tailored by ${siteContent.company} based on your rollout scope.`
  const cardCta = lang === 'vi' ? 'Chọn gói này' : 'Choose this plan'
  const includeText = lang === 'vi' ? 'Bao gồm' : 'Includes'

  return (
    <SiteShell>
      <section className="container py-16 md:py-20">
        <p className="kicker mb-4">
          <span className="dot" />
          Pricing
        </p>
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">{title}</h1>
        <p className="mt-4 max-w-2xl text-slate-600 text-lg">
          {desc}
        </p>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {planCards.map((plan, index) => (
            <article className={`card pricing-card p-6 ${index === 1 ? 'pricing-card-featured' : ''}`} key={plan.name}>
              {index === 1 && <span className="pricing-badge">Khuyen nghi</span>}
              <h2 className="text-xl font-semibold">{plan.name}</h2>
              <p className="mt-2 text-sm text-slate-600 min-h-[40px]">{plan.summary}</p>
              <p className="mt-4 text-xs uppercase tracking-[0.08em] text-slate-500">{includeText}</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-700">
                {plan.highlights.map(item => (
                  <li className="pricing-item" key={item}>{item}</li>
                ))}
              </ul>
              <a className={`btn mt-6 w-full ${index === 1 ? 'btn-primary' : 'btn-secondary'}`} href="/signin">
                {cardCta}
              </a>
            </article>
          ))}
        </div>
      </section>
      <section className="container pb-16">
        <div className="card final-cta p-8 text-center">
          <h2 className="text-2xl font-bold">{ctaTitle}</h2>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <a className="btn btn-primary" href="/signin">
              {ctaPrimary}
            </a>
            <a className="btn btn-secondary" href="/contact">
              {ctaSecondary}
            </a>
          </div>
          <p className="mt-4 text-sm text-slate-500">{note}</p>
        </div>
      </section>
    </SiteShell>
  )
}
