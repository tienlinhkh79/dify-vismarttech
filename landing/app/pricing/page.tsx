'use client'

import { usePreferences } from '@/components/preferences-context'
import SiteShell from '@/components/site-shell'
import { planCards, siteContent } from '@/content/site'
import { links } from '@/lib/links'

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

  return (
    <SiteShell>
      <section className="container py-16 md:py-20">
        <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          {desc}
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {planCards.map(plan => (
            <article className="card p-6" key={plan.name}>
              <h2 className="text-xl font-semibold">{plan.name}</h2>
              <p className="mt-2 text-sm text-slate-600">{plan.summary}</p>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {plan.highlights.map(item => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>
      <section className="container pb-16">
        <div className="card p-8 text-center">
          <h2 className="text-2xl font-bold">{ctaTitle}</h2>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <a className="btn btn-primary" href={links.signin}>
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
