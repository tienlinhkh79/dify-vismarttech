import SiteShell from '@/components/site-shell'
import { siteContent } from '@/content/site'
import { links } from '@/lib/links'

export default function ContactPage() {
  return (
    <SiteShell>
      <section className="container py-16 md:py-20">
        <h1 className="text-4xl font-bold tracking-tight">Liên hệ đội ngũ {siteContent.company}</h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          Gửi nhu cầu triển khai, đội ngũ sẽ tư vấn lộ trình phù hợp theo quy mô và nghiệp vụ doanh nghiệp.
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          <article className="card p-6">
            <h2 className="text-lg font-semibold">Tư vấn giải pháp</h2>
            <p className="mt-2 text-sm text-slate-600">Dành cho báo giá, lựa chọn gói và thiết kế lộ trình triển khai.</p>
            <a className="mt-4 inline-block font-medium text-blue-700 hover:text-blue-800" href={`mailto:${siteContent.contacts.salesEmail}`}>
              {siteContent.contacts.salesEmail}
            </a>
          </article>
          <article className="card p-6">
            <h2 className="text-lg font-semibold">Hỗ trợ kỹ thuật</h2>
            <p className="mt-2 text-sm text-slate-600">Dành cho cài đặt, tích hợp hệ thống và hỗ trợ production.</p>
            <a className="mt-4 inline-block font-medium text-blue-700 hover:text-blue-800" href={`mailto:${siteContent.contacts.supportEmail}`}>
              {siteContent.contacts.supportEmail}
            </a>
          </article>
        </div>
      </section>
      <section className="container pb-16">
        <div className="card p-8 text-center">
          <h2 className="text-2xl font-bold">Muốn trải nghiệm ngay?</h2>
          <div className="mt-6 flex justify-center">
            <a className="btn btn-primary" href={links.signin}>
              Vào hệ thống ngay
            </a>
          </div>
        </div>
      </section>
    </SiteShell>
  )
}
