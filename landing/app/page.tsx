import SiteShell from '@/components/site-shell'
import WorkflowFlow from '@/components/workflow-flow'
import { planCards, siteContent } from '@/content/site'
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

export default function HomePage() {
  return (
    <SiteShell>
      <section className="container py-16 md:py-24">
        <div className="card hero-gradient grid gap-10 p-8 md:grid-cols-2 md:p-12">
          <div>
            <p className="mb-4 inline-flex rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
              {siteContent.product}
            </p>
            <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl">{siteContent.tagline}</h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">
              {siteContent.description}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a className="btn btn-primary" href={links.signin}>
                Dùng thử miễn phí
              </a>
              <a className="btn btn-secondary" href={links.register}>
                Đăng ký
              </a>
              <a className="btn btn-secondary" href="#features">
                Xem tính năng
              </a>
            </div>
          </div>
          <div className="card flex flex-col gap-4 p-5">
            <p className="text-sm font-medium text-slate-600">Năng lực cốt lõi</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {siteContent.metrics.map(metric => (
                <article className="card bg-white p-4" key={metric.label}>
                  <p className="text-xl font-bold">{metric.value}</p>
                  <p className="mt-1 text-xs text-slate-600">{metric.label}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="container py-10 md:py-14" id="features">
        <h2 className="section-title">Tất cả thành phần cần thiết để vận hành AI production</h2>
        <p className="mt-3 max-w-2xl text-slate-600">
          Được thiết kế cho team vận hành, sản phẩm và kỹ thuật triển khai AI đồng bộ từ một hệ thống.
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
        <h2 className="section-title">Hình ảnh sản phẩm và video demo</h2>
        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          <article className="card p-4">
            <img
              alt="Vismarttech dashboard preview"
              className="h-[280px] w-full rounded-xl border border-[var(--border)] object-cover"
              src="https://images.unsplash.com/photo-1551281044-8b7ea3d8f6ab?auto=format&fit=crop&w=1400&q=80"
            />
            <p className="mt-3 text-sm text-slate-600">Giao diện vận hành dashboard, analytics và quality tracking.</p>
          </article>
          <article className="card p-4">
            <div className="overflow-hidden rounded-xl border border-[var(--border)]">
              <iframe
                title="Vismarttech product demo"
                className="h-[280px] w-full"
                src="https://www.youtube.com/embed/dQw4w9WgXcQ"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
            <p className="mt-3 text-sm text-slate-600">Video demo luồng tư vấn tự động và xử lý ticket đa kênh.</p>
          </article>
        </div>
      </section>

      <section className="container py-10 md:py-14" id="social-proof">
        <h2 className="section-title">Được tin dùng bởi các đội triển khai nhanh</h2>
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
        <h2 className="section-title">Gói dịch vụ theo quy mô doanh nghiệp</h2>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {planCards.map(plan => (
            <article className="card p-5" key={plan.name}>
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
        <h2 className="section-title">Quy trình triển khai cùng Vismarttech</h2>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {rolloutSteps.map(step => (
            <article className="card p-5" key={step.title}>
              <h3 className="text-lg font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.detail}</p>
            </article>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-2">
          {platformTags.map(tag => (
            <span className="rounded-full border border-[var(--border)] bg-white px-3 py-1 text-xs text-slate-600" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      </section>

      <section className="container py-16 md:py-20">
        <div className="card p-8 text-center md:p-12">
          <h2 className="text-3xl font-bold tracking-tight">Bắt đầu triển khai AI cùng {siteContent.company}</h2>
          <p className="mx-auto mt-3 max-w-2xl text-slate-600">
            Chuẩn hóa triển khai chatbot, knowledge base và automation cho doanh nghiệp của bạn trên một nền tảng thống nhất.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <a className="btn btn-primary" href={links.signin}>
              Tạo workspace
            </a>
            <a className="btn btn-secondary" href={links.app}>
              Vào hệ thống
            </a>
          </div>
        </div>
      </section>
    </SiteShell>
  )
}
