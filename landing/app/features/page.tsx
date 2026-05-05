'use client'

import { usePreferences } from '@/components/preferences-context'
import { copy } from '@/content/i18n'
import SiteShell from '@/components/site-shell'
import { siteContent } from '@/content/site'
import { links } from '@/lib/links'

const sections = [
  {
    title: 'Workflow AI Orchestration',
    points: ['Trình thiết kế workflow trực quan nhiều bước', 'Chuẩn hóa luồng xử lý cho chatbot và tác vụ nội bộ'],
  },
  {
    title: 'Knowledge Base & RAG',
    points: ['Nạp dữ liệu đa nguồn và truy xuất có kiểm soát', 'Grounded response ổn định cho nghiệp vụ doanh nghiệp'],
  },
  {
    title: 'Omnichannel & CRM',
    points: ['Kết nối đa kênh và đồng bộ chăm sóc khách hàng', 'Quản lý lead và hội thoại tập trung'],
  },
]

export default function FeaturesPage() {
  const { lang } = usePreferences()
  const t = copy[lang]
  const intro = lang === 'vi'
    ? `Năng lực nền tảng của ${siteContent.company}`
    : `${siteContent.company} platform capabilities`
  const desc = lang === 'vi'
    ? 'Bộ tính năng được tổ chức theo nhu cầu triển khai AI thực tế: từ thiết kế flow, quản trị dữ liệu tri thức đến vận hành và chăm sóc khách hàng đa kênh.'
    : 'Feature modules are organized for real-world AI delivery: from workflow design and knowledge operations to omnichannel customer support.'
  const ctaTitle = lang === 'vi' ? 'Sẵn sàng đưa AI vào production?' : 'Ready to move AI into production?'
  const ctaButton = lang === 'vi' ? 'Bắt đầu ngay' : 'Get Started'

  return (
    <SiteShell>
      <section className="container py-16 md:py-20">
        <h1 className="text-4xl font-bold tracking-tight">{intro}</h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          {desc}
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {sections.map(section => (
            <article className="card p-5" key={section.title}>
              <h2 className="text-lg font-semibold">{section.title}</h2>
              <ul className="mt-3 space-y-2 text-sm text-slate-600">
                {section.points.map(point => (
                  <li key={point}>- {point}</li>
                ))}
              </ul>
            </article>
          ))}
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
