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
  return (
    <SiteShell>
      <section className="container py-16 md:py-20">
        <h1 className="text-4xl font-bold tracking-tight">Năng lực nền tảng của {siteContent.company}</h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          Bộ tính năng được tổ chức theo nhu cầu triển khai AI thực tế: từ thiết kế flow, quản trị dữ liệu
          tri thức đến vận hành và chăm sóc khách hàng đa kênh.
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
          <h2 className="text-2xl font-bold">Sẵn sàng đưa AI vào production?</h2>
          <div className="mt-6 flex justify-center">
            <a className="btn btn-primary" href={links.signin}>
              Bắt đầu ngay
            </a>
          </div>
        </div>
      </section>
    </SiteShell>
  )
}
