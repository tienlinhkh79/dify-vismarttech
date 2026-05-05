'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'
import { siteContent } from '@/content/site'
import { links } from '@/lib/links'

type SiteShellProps = {
  children: ReactNode
}

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/contact', label: 'Contact' },
]

export default function SiteShell({ children }: SiteShellProps) {
  const pathname = usePathname()
  const year = new Date().getFullYear()

  return (
    <main>
      <header className="container flex items-center justify-between py-6">
        <Link className="flex items-center gap-3 text-xl font-bold tracking-tight" href="/">
          <img alt={`${siteContent.company} logo`} className="h-8 w-auto" src="/vismarttech-logo.png" />
          <span>{siteContent.company}</span>
        </Link>
        <nav className="flex items-center gap-6 text-sm text-slate-700" aria-label="Primary">
          {navItems.map(item => (
            <Link
              aria-current={pathname === item.href ? 'page' : undefined}
              className={`nav-link ${pathname === item.href ? 'nav-link-active' : ''}`}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          ))}
          <a className="nav-link" href={links.signin} target="_blank" rel="noreferrer">Login</a>
          <a className="btn btn-secondary" href={links.register} target="_blank" rel="noreferrer">Register</a>
          <a className="btn btn-primary" href={links.app} target="_blank" rel="noreferrer">Go to App</a>
        </nav>
      </header>
      {children}

      <footer className="border-t border-[var(--border)] bg-white/70">
        <div className="container py-12">
          <div className="grid gap-8 md:grid-cols-4">
            <section>
              <p className="footer-title">Về {siteContent.company}</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">{siteContent.description}</p>
            </section>

            <section>
              <p className="footer-title">Giải pháp</p>
              <div className="mt-3 flex flex-col gap-2 text-sm text-slate-600">
                <Link href="/features">Workflow AI</Link>
                <Link href="/features">Knowledge Base</Link>
                <Link href="/features">Omnichannel</Link>
                <Link href="/pricing">Bảng gói dịch vụ</Link>
              </div>
            </section>

            <section>
              <p className="footer-title">Liên hệ</p>
              <div className="mt-3 flex flex-col gap-2 text-sm text-slate-600">
                <a href={`mailto:${siteContent.contacts.salesEmail}`}>{siteContent.contacts.salesEmail}</a>
                <a href={`mailto:${siteContent.contacts.supportEmail}`}>{siteContent.contacts.supportEmail}</a>
                <span>{siteContent.contacts.hotline}</span>
                <span>{siteContent.contacts.address}</span>
              </div>
            </section>

            <section>
              <p className="footer-title">Kết nối</p>
              <div className="mt-3 flex flex-col gap-2 text-sm text-slate-600">
                {siteContent.socials.map(item => (
                  <a href={item.href} key={item.label} target="_blank" rel="noreferrer">
                    {item.label}
                  </a>
                ))}
              </div>
            </section>
          </div>

          <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] pt-5 text-xs text-slate-500">
            <p>{siteContent.company} - Nền tảng AI cho vận hành doanh nghiệp.</p>
            <p>Copyright {year} {siteContent.company}. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </main>
  )
}
