import SiteShell from '@/components/site-shell'
import { planCards, siteContent } from '@/content/site'
import { links } from '@/lib/links'

export default function PricingPage() {
  return (
    <SiteShell>
      <section className="container py-16 md:py-20">
        <h1 className="text-4xl font-bold tracking-tight">Bảng gói dịch vụ theo quy mô sử dụng</h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          Cấu trúc gói được ánh xạ từ giới hạn vận hành trong hệ thống để dễ nâng cấp theo từng giai đoạn tăng trưởng.
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
          <h2 className="text-2xl font-bold">Cần tư vấn gói phù hợp?</h2>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <a className="btn btn-primary" href={links.signin}>
              Tạo workspace
            </a>
            <a className="btn btn-secondary" href="/contact">
              Liên hệ tư vấn
            </a>
          </div>
          <p className="mt-4 text-sm text-slate-500">Bảng giá chi tiết sẽ được đội ngũ {siteContent.company} tư vấn theo nhu cầu triển khai.</p>
        </div>
      </section>
    </SiteShell>
  )
}
