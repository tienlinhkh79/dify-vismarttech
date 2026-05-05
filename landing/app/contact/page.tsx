'use client'

import { usePreferences } from '@/components/preferences-context'
import SiteShell from '@/components/site-shell'
import { siteContent } from '@/content/site'
import { links } from '@/lib/links'

export default function ContactPage() {
  const { lang } = usePreferences()
  const title = lang === 'vi' ? `Liên hệ đội ngũ ${siteContent.company}` : `Contact the ${siteContent.company} team`
  const desc = lang === 'vi'
    ? 'Gửi nhu cầu triển khai, đội ngũ sẽ tư vấn lộ trình phù hợp theo quy mô và nghiệp vụ doanh nghiệp.'
    : 'Share your implementation goals and our team will propose a rollout plan based on your business scale.'
  const salesTitle = lang === 'vi' ? 'Tư vấn giải pháp' : 'Solution consulting'
  const salesDesc = lang === 'vi'
    ? 'Dành cho báo giá, lựa chọn gói và thiết kế lộ trình triển khai.'
    : 'For pricing, plan selection, and rollout architecture.'
  const supportTitle = lang === 'vi' ? 'Hỗ trợ kỹ thuật' : 'Technical support'
  const supportDesc = lang === 'vi'
    ? 'Dành cho cài đặt, tích hợp hệ thống và hỗ trợ production.'
    : 'For setup, integrations, and production support.'
  const ctaTitle = lang === 'vi' ? 'Muốn trải nghiệm ngay?' : 'Prefer self-serve?'
  const ctaButton = lang === 'vi' ? 'Vào hệ thống ngay' : 'Open Platform'

  return (
    <SiteShell>
      <section className="container py-16 md:py-20">
        <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          {desc}
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          <article className="card p-6">
            <h2 className="text-lg font-semibold">{salesTitle}</h2>
            <p className="mt-2 text-sm text-slate-600">{salesDesc}</p>
            <a className="mt-4 inline-block font-medium text-blue-700 hover:text-blue-800" href={`mailto:${siteContent.contacts.salesEmail}`}>
              {siteContent.contacts.salesEmail}
            </a>
          </article>
          <article className="card p-6">
            <h2 className="text-lg font-semibold">{supportTitle}</h2>
            <p className="mt-2 text-sm text-slate-600">{supportDesc}</p>
            <a className="mt-4 inline-block font-medium text-blue-700 hover:text-blue-800" href={`mailto:${siteContent.contacts.supportEmail}`}>
              {siteContent.contacts.supportEmail}
            </a>
          </article>
        </div>
      </section>
      <section className="container pb-16">
        <div className="card p-8 text-center">
          <h2 className="text-2xl font-bold">{ctaTitle}</h2>
          <div className="mt-6 flex justify-center">
            <a className="btn btn-primary" href={links.signin}>
              {ctaButton}
            </a>
          </div>
        </div>
      </section>
    </SiteShell>
  )
}
