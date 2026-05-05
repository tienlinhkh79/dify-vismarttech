'use client'

import { usePreferences } from '@/components/preferences-context'
import { copy } from '@/content/i18n'
import ProductMockup from '@/components/product-mockup'
import SiteShell from '@/components/site-shell'
import WorkflowFlow from '@/components/workflow-flow'
import { planCards } from '@/content/site'
import { links } from '@/lib/links'

const featureList = [
  {
    title: 'Visual Workflow Builder',
    description: 'Design and iterate AI pipelines without bottlenecking on backend cycles.',
  },
  {
    title: 'Production-Grade RAG',
    description: 'Connect your data sources and deliver grounded responses with confidence.',
  },
  {
    title: 'Agent + Tool Ecosystem',
    description: 'Equip assistants with tools, memory, and integrations for real operations.',
  },
]

const testimonials = [
  {
    quote: 'Chúng tôi giảm thời gian triển khai chatbot nội bộ từ vài tuần xuống vài ngày.',
    author: 'Giám đốc Sản phẩm, doanh nghiệp dịch vụ',
  },
  {
    quote: 'Team vận hành có thể tự build flow mà không phụ thuộc hoàn toàn vào kỹ thuật.',
    author: 'Trưởng bộ phận Vận hành, fintech',
  },
  {
    quote: 'Một nền tảng cho cả POC và production, không cần di chuyển hệ thống.',
    author: 'CTO, công ty tư vấn AI',
  },
  {
    quote: 'Dashboard rõ ràng giúp chúng tôi đo được chất lượng phản hồi theo từng kênh.',
    author: 'Head of CX, thương mại điện tử',
  },
  {
    quote: 'Tích hợp webhook giúp team IT kết nối CRM hiện có mà không phải thay đổi hạ tầng.',
    author: 'IT Manager, dịch vụ tài chính',
  },
]

const rolloutSteps = [
  {
    title: 'Khảo sát nghiệp vụ',
    detail: 'Xác định luồng vận hành, dữ liệu đầu vào và KPI đo lường cho từng phòng ban.',
  },
  {
    title: 'Thiết kế workflow AI',
    detail: 'Xây dựng workflow, chuẩn hóa prompt, kết nối knowledge base và công cụ nội bộ.',
  },
  {
    title: 'Triển khai & tối ưu',
    detail: 'Đưa vào production, theo dõi chất lượng phản hồi và tối ưu liên tục theo dữ liệu thực tế.',
  },
]

const platformTags = ['OpenAI', 'Anthropic', 'Gemini', 'DeepSeek', '9Pay', 'Zalo OA', 'Messenger', 'Webhook API']
const coreMetrics = [
  { label: 'Kênh Omnichannel', value: '100+' },
  { label: 'Ứng dụng nội bộ', value: '200+' },
  { label: 'Knowledge API / phút', value: '1000' },
]
const faqs = [
  {
    q: 'Vismarttech phù hợp doanh nghiệp quy mô nào?',
    a: 'Từ đội nhỏ cần POC nhanh đến doanh nghiệp nhiều phòng ban cần vận hành omnichannel và automation ở production.',
  },
  {
    q: 'Mất bao lâu để triển khai hệ thống đầu tiên?',
    a: 'Thông thường 2-4 tuần cho pilot, tùy theo độ sẵn sàng dữ liệu và số lượng tích hợp bên thứ ba.',
  },
  {
    q: 'Có hỗ trợ tích hợp hệ thống CRM/ERP hiện có không?',
    a: 'Có. Nền tảng hỗ trợ webhook/API để kết nối với CRM, ERP, ticketing và các hệ thống nội bộ.',
  },
  {
    q: 'Dữ liệu doanh nghiệp có được phân quyền không?',
    a: 'Có. Workspace, knowledge base và kênh vận hành có thể được phân quyền theo đội nhóm.',
  },
  {
    q: 'Có thể triển khai theo hạ tầng riêng không?',
    a: 'Có thể triển khai self-hosted hoặc cấu hình theo yêu cầu bảo mật của doanh nghiệp.',
  },
]

export default function HomePage() {
  const { lang } = usePreferences()
  const t = copy[lang].home

  return (
    <SiteShell>
      <section className="container py-10 md:py-16">
        <div className="card hero-gradient grid gap-10 p-8 md:grid-cols-2 md:p-12">
          <div>
            <p className="kicker mb-4 animate-fade-up">
              <span className="dot" />
              {t.product}
            </p>
            <h1 className="animate-fade-up delay-1 text-4xl font-bold leading-tight tracking-tight md:text-6xl">{t.tagline}</h1>
            <p className="animate-fade-up delay-2 mt-5 max-w-xl text-lg leading-8 text-slate-600">
              {t.description}
            </p>
            <div className="animate-fade-up delay-3 mt-8 flex flex-wrap gap-3">
              <a className="btn btn-primary" href={links.signin}>
                {t.ctaFree}
              </a>
              <a className="btn btn-secondary" href={links.register}>
                {t.ctaRegister}
              </a>
              <a className="btn btn-secondary" href="#features">
                {t.ctaFeatures}
              </a>
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              {platformTags.map(tag => (
                <span className="rounded-full border border-[var(--border)] bg-white px-3 py-1 text-xs text-slate-600" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
          <div className="animate-fade-up delay-2 flex flex-col gap-4">
            <ProductMockup />
            <div className="card flex flex-col gap-4 p-5">
              <p className="text-sm font-medium text-slate-600">Năng lực cốt lõi</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {coreMetrics.map(metric => (
                  <article className="card bg-white p-4" key={metric.label}>
                    <p className="text-xl font-bold">{metric.value}</p>
                    <p className="mt-1 text-xs text-slate-600">{metric.label}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container py-10 md:py-14" id="features">
        <h2 className="section-title">{t.titleFeature}</h2>
        <p className="mt-3 max-w-2xl text-slate-600">
          {t.subtitleFeature}
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {featureList.map(item => (
            <article className="card p-5" key={item.title}>
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
            </article>
          ))}
        </div>
        <WorkflowFlow />
      </section>

      <section className="container py-8 md:py-14">
        <h2 className="section-title">{t.mediaTitle}</h2>
        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          <article className="card p-4">
            <img
              alt="Vismarttech dashboard preview"
              className="h-[280px] w-full rounded-xl border border-[var(--border)] object-cover"
              src="https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1400&q=80"
            />
            <p className="mt-3 text-sm text-slate-600">{t.mediaDesc1}</p>
          </article>
          <article className="card p-4">
            <div className="overflow-hidden rounded-xl border border-[var(--border)]">
              <iframe
                title="Vismarttech product demo"
                className="h-[280px] w-full"
                src="https://www.youtube.com/embed/jfKfPfyJRdk"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
            <p className="mt-3 text-sm text-slate-600">{t.mediaDesc2}</p>
          </article>
        </div>
      </section>

      <section className="container py-10 md:py-14" id="social-proof">
        <h2 className="section-title">{t.trustTitle}</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {testimonials.map(item => (
            <article className="card p-5" key={item.author}>
              <p className="text-sm leading-6 text-slate-700">&ldquo;{item.quote}&rdquo;</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {item.author}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="container py-8 md:py-14">
        <h2 className="section-title">{t.pricingTitle}</h2>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {planCards.map((plan, index) => (
            <article className={`card p-5 ${index === 1 ? 'card-featured' : ''}`} key={plan.name}>
              {index === 1 && (
                <span className="inline-flex rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white">{t.recommended}</span>
              )}
              <h3 className="text-lg font-semibold">{plan.name}</h3>
              <p className="mt-1 text-sm text-slate-600">{plan.summary}</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-700">
                {plan.highlights.map(item => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="container py-8 md:py-14">
        <h2 className="section-title">{t.processTitle}</h2>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {rolloutSteps.map(step => (
            <article className="card p-5" key={step.title}>
              <h3 className="text-lg font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.detail}</p>
            </article>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-2">
          <span className="text-sm text-slate-500">{t.processDesc}</span>
        </div>
      </section>

      <section className="container py-16 md:py-20">
        <div className="card final-cta p-8 text-center md:p-12">
          <h2 className="text-3xl font-bold tracking-tight">{t.finalTitle}</h2>
          <p className="mx-auto mt-3 max-w-2xl text-slate-600">
            {t.finalDesc}
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <a className="btn btn-primary" href={links.signin}>
              {t.finalCta1}
            </a>
            <a className="btn btn-secondary" href={links.app}>
              {t.finalCta2}
            </a>
          </div>
          <form className="relative z-10 mx-auto mt-6 flex max-w-md flex-wrap justify-center gap-2">
            <input aria-label={t.newsletterPlaceholder} className="newsletter-input flex-1" placeholder={t.newsletterPlaceholder} type="email" />
            <button className="btn btn-primary" type="button">{t.newsletterCta}</button>
          </form>
        </div>
      </section>

      <section className="container pb-20">
        <h2 className="section-title">{t.faqTitle}</h2>
        <div className="mt-6 grid gap-3">
          {faqs.map(item => (
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
