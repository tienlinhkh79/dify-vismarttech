'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, type ReactNode } from 'react'
import { usePreferences } from '@/components/preferences-context'
import { copy } from '@/content/i18n'
import { siteContent } from '@/content/site'
import { links } from '@/lib/links'

type SiteShellProps = {
  children: ReactNode
}

const navItems = [
  { href: '/' },
  { href: '/features' },
  { href: '/pricing' },
  { href: '/contact' },
]

function SunIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M21 14.2A8.4 8.4 0 0 1 9.8 3 8.8 8.8 0 1 0 21 14.2Z" />
    </svg>
  )
}

function GlobeIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" />
      <path d="M3.6 9h16.8M3.6 15h16.8M12 3c2.2 2.5 3.4 5.5 3.4 9S14.2 18.5 12 21c-2.2-2.5-3.4-5.5-3.4-9S9.8 5.5 12 3Z" />
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

function ChatbotIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 56 56">
      <path d="M12.5 24.5c0-7 5.7-12.5 12.7-12.5h5.6c7 0 12.7 5.5 12.7 12.5v3.6c0 7-5.7 12.5-12.7 12.5H26L19 46v-5.6a12.7 12.7 0 0 1-6.5-11.1v-4.8Z" />
      <path d="M21.8 27.8h.1M34.2 27.8h.1M22.8 34c2.9 2.1 7.5 2.1 10.4 0" />
      <path d="M40.6 13.8v4.8M38.2 16.2H43M15.8 13.8v4.8M13.4 16.2h4.8" />
    </svg>
  )
}

export default function SiteShell({ children }: SiteShellProps) {
  const pathname = usePathname()
  const year = new Date().getFullYear()
  const [mobileOpen, setMobileOpen] = useState(false)
  const { lang, setLang, theme, setTheme } = usePreferences()
  const t = copy[lang]

  const getLabel = (href: string) =>
    href === '/' ? t.nav.home : href === '/features' ? t.nav.features : href === '/pricing' ? t.nav.pricing : t.nav.contact

  return (
    <main>
      <header className="container sticky top-4 z-20 py-4">
        <div className="glass-header grid grid-cols-[1fr_auto_1fr] items-center gap-4 rounded-2xl px-5 py-3">
          <Link className="flex items-center" href="/" aria-label={siteContent.company}>
            <img alt={`${siteContent.company} logo`} className="h-8 w-auto" src="/vismarttech-logo.png" />
          </Link>

          <button
            aria-expanded={mobileOpen}
            aria-label="Toggle menu"
            className="icon-button mobile-menu-button justify-self-end"
            onClick={() => setMobileOpen(prev => !prev)}
            type="button"
          >
            <MenuIcon />
          </button>

          <nav className="desktop-nav contents text-sm text-slate-700" aria-label="Primary">
            <div className="flex items-center justify-center gap-5">
              {navItems.map(item => (
                <Link
                  aria-current={pathname === item.href ? 'page' : undefined}
                  className={`nav-link ${pathname === item.href ? 'nav-link-active' : ''}`}
                  href={item.href}
                  key={item.href}
                >
                  {getLabel(item.href)}
                </Link>
              ))}
            </div>
            <div className="utility-dock justify-self-end" aria-label="Quick actions">
              <button
                aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
                aria-pressed={theme === 'dark'}
                className="icon-button"
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                type="button"
              >
                {theme === 'light' ? <MoonIcon /> : <SunIcon />}
              </button>
              <button
                aria-label={lang === 'vi' ? 'Switch to English' : 'Chuyển tiếng Việt'}
                className="icon-button language-button"
                onClick={() => setLang(lang === 'vi' ? 'en' : 'vi')}
                type="button"
              >
                <GlobeIcon />
                <span>{lang === 'vi' ? 'EN' : 'VI'}</span>
              </button>
              <a className="btn btn-primary header-cta" href={links.app} target="_blank" rel="noreferrer">{t.nav.app}</a>
            </div>
          </nav>
        </div>

        {mobileOpen && (
          <div className="glass-header mobile-panel mt-3 rounded-2xl p-4">
            <nav className="flex flex-col gap-3 text-sm" aria-label="Mobile primary">
              {navItems.map(item => (
                <Link className={`nav-link ${pathname === item.href ? 'nav-link-active' : ''}`} href={item.href} key={item.href}>
                  {getLabel(item.href)}
                </Link>
              ))}
              <div className="utility-dock w-full justify-between">
                <button
                  aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
                  className="icon-button"
                  onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                  type="button"
                >
                  {theme === 'light' ? <MoonIcon /> : <SunIcon />}
                </button>
                <button
                  aria-label={lang === 'vi' ? 'Switch to English' : 'Chuyển tiếng Việt'}
                  className="icon-button language-button"
                  onClick={() => setLang(lang === 'vi' ? 'en' : 'vi')}
                  type="button"
                >
                  <GlobeIcon />
                  <span>{lang === 'vi' ? 'EN' : 'VI'}</span>
                </button>
              </div>
              <a className="btn btn-primary w-full" href={links.app} target="_blank" rel="noreferrer">{t.nav.app}</a>
            </nav>
          </div>
        )}
      </header>
      {children}

      <aside className="floating-contact" aria-label="Quick contact">
        <a aria-label="Chatbot" className="floating-contact-button floating-contact-chatbot" href={links.app}>
          <ChatbotIcon />
        </a>
      </aside>

      <footer className="border-t border-[var(--border)] bg-white/70">
        <div className="container py-12">
          <div className="grid gap-8 md:grid-cols-4">
            <section>
              <p className="footer-title">{t.footer.about} {siteContent.company}</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">{t.footer.aboutDesc}</p>
            </section>

            <section>
              <p className="footer-title">{t.footer.solutions}</p>
              <div className="mt-3 flex flex-col gap-2 text-sm text-slate-600">
                <Link href="/features">Workflow AI</Link>
                <Link href="/features">Knowledge Base</Link>
                <Link href="/features">Omnichannel</Link>
                <Link href="/pricing">{t.footer.plans}</Link>
              </div>
            </section>

            <section>
              <p className="footer-title">{t.footer.contact}</p>
              <div className="mt-3 flex flex-col gap-2 text-sm text-slate-600">
                <a href={`mailto:${siteContent.contacts.salesEmail}`}>{siteContent.contacts.salesEmail}</a>
                <a href={`mailto:${siteContent.contacts.supportEmail}`}>{siteContent.contacts.supportEmail}</a>
                <span>{siteContent.contacts.hotline}</span>
                <span>{siteContent.contacts.address}</span>
              </div>
            </section>

            <section>
              <p className="footer-title">{t.footer.connect}</p>
              <div className="mt-3 flex flex-col gap-2 text-sm text-slate-600">
                {siteContent.socials.map(item => (
                  <a href={item.href} key={item.label} target="_blank" rel="noreferrer">
                    {item.label}
                  </a>
                ))}
              </div>
            </section>
          </div>

          <div className="mt-8 grid gap-4 border-t border-[var(--border)] pt-5 md:grid-cols-[1fr_auto] md:items-center">
            <div className="flex flex-wrap gap-3 text-xs text-slate-500">
              <span>{t.footer.legal}</span>
              <a href="/privacy">{t.footer.privacy}</a>
              <a href="/terms">{t.footer.terms}</a>
            </div>
            <form className="flex flex-wrap gap-2">
              <input aria-label="Newsletter email" className="newsletter-input" placeholder={t.home.newsletterPlaceholder} type="email" />
              <button className="btn btn-secondary" type="button">{t.home.newsletterCta}</button>
            </form>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
            <p>{siteContent.company} - {t.footer.line}</p>
            <p>Copyright {year} {siteContent.company}. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </main>
  )
}
