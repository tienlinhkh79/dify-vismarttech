'use client'

import { useRef } from 'react'
import Image from 'next/image'

import { HubChannelTile } from '@/components/brand-icons'
import { HubConnectorLines } from '@/components/hub-connector-lines'
import { HERO_CHAT_PRODUCT_IMAGE, HERO_CRM_AVATARS } from '@/content/module-placeholders'
import type { HomeCopy } from '@/content/home-content'

type HeroShowcaseProps = {
  content: HomeCopy['hero']['showcase']
  variant?: 'section' | 'inline'
}

const RM_VALUES = { total: 454, viewed: 312, clicked: 100, failed: 0 } as const

const GENDER_SYMBOLS = ['♂', '♀', '♂'] as const

type RemarketingStatRow = {
  label: string
  value: number
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'muted'
}

function hubTagClass(tag: string): string {
  const t = tag.toLowerCase()
  if (t.includes('ticket'))
    return 'hub-tag hub-tag--ticket'
  if (t.includes('new') || t.includes('mới'))
    return 'hub-tag hub-tag--new'
  if (t.includes('zalo'))
    return 'hub-tag hub-tag--zalo'
  if (t.includes('vip'))
    return 'hub-tag hub-tag--vip'
  if (t.includes('appointment') || t.includes('lịch'))
    return 'hub-tag hub-tag--appointment'
  if (t.includes('loyal') || t.includes('trung thành'))
    return 'hub-tag hub-tag--loyal'
  return 'hub-tag hub-tag--default'
}

function StatusIcon({ kind }: { kind: 'box' | 'chart' | 'bell' | 'cart' }) {
  if (kind === 'box') {
    return (
      <svg aria-hidden className="hub-crm-status-icon" viewBox="0 0 16 16">
        <path d="M2 4.5 8 1.5l6 3v7L8 14.5l-6-3v-7Z" fill="none" stroke="currentColor" strokeWidth="1.2" />
        <path d="M8 8v6.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
        <path d="M2 4.5 8 8l6-3.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
      </svg>
    )
  }
  if (kind === 'chart') {
    return (
      <svg aria-hidden className="hub-crm-status-icon" viewBox="0 0 16 16">
        <path d="M3 13V8M8 13V4M13 13V6" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
      </svg>
    )
  }
  if (kind === 'bell') {
    return (
      <svg aria-hidden className="hub-crm-status-icon" viewBox="0 0 16 16">
        <path d="M8 2.5a3.5 3.5 0 0 0-3.5 3.5v2.2L3 10.5h10l-1.5-2.3V6A3.5 3.5 0 0 0 8 2.5Z" fill="none" stroke="currentColor" strokeWidth="1.2" />
        <path d="M6.5 10.5a1.5 1.5 0 0 0 3 0" fill="none" stroke="currentColor" strokeWidth="1.2" />
      </svg>
    )
  }
  return (
    <svg aria-hidden className="hub-crm-status-icon" viewBox="0 0 16 16">
      <circle cx="6" cy="13" fill="none" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="12" cy="13" fill="none" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <path d="M2 3h2l1.2 6.5a1 1 0 0 0 1 .8h5.6a1 1 0 0 0 1-.8L14 5h-9" fill="none" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

export default function HeroShowcase({ content, variant = 'inline' }: HeroShowcaseProps) {
  const rm = content.remarketing
  const stats: RemarketingStatRow[] = [
    { label: rm.total, value: RM_VALUES.total, tone: 'default' },
    { label: rm.viewed, value: RM_VALUES.viewed, tone: 'success' },
    { label: rm.clicked, value: RM_VALUES.clicked, tone: 'warning' },
    { label: rm.failed, value: RM_VALUES.failed, tone: 'danger' },
  ]

  const statusIcons: Array<{ activity?: 'box' | 'chart' | 'bell' | 'cart'; status: 'box' | 'chart' | 'bell' | 'cart' }> = [
    { activity: 'box', status: 'chart' },
    { activity: 'box', status: 'bell' },
    { status: 'cart' },
  ]

  const hubClass = variant === 'section'
    ? 'hero-hub hero-hub--section feature-showcase-inner'
    : 'hero-hub'
  const gridRef = useRef<HTMLDivElement>(null)

  return (
    <div className={hubClass}>
      <div aria-hidden className="hero-hub-glow" />

      <div className="hero-hub-stage">
        <div className="hero-hub-grid" ref={gridRef}>
        <div className="hero-hub-col hero-hub-col--left">
          <article className="hub-card hub-card--chat" data-hub-anchor="chat">
            <header className="hub-chat-head">
              <span aria-hidden className="hub-chat-head-icon">
                <svg viewBox="0 0 24 24">
                  <path d="M12 3a7 7 0 0 0-7 7v3.5L3 17h18l-2-3.5V10a7 7 0 0 0-7-7Z" fill="currentColor" opacity="0.9" />
                </svg>
              </span>
              <div>
                <p className="hub-card-title">{content.chatTitle}</p>
                <p className="hub-card-subtitle">{content.chatShop}</p>
              </div>
            </header>
            <div className="hub-chat-body">
              <div className="hub-chat-product">
                <Image
                  alt=""
                  className="hub-chat-product-img"
                  height={168}
                  src={HERO_CHAT_PRODUCT_IMAGE}
                  width={120}
                />
              </div>
              <div className="hub-chat-thread">
                <div className="hub-bubble hub-bubble--user">{content.chatQuestion}</div>
                <div className="hub-bubble hub-bubble--ai">{content.chatAnswer}</div>
              </div>
            </div>
          </article>

          <article className="hub-card hub-card--channels" data-hub-anchor="channels">
            <p className="hub-card-title hub-card-title--compact">{content.channelsTitle}</p>
            <div className="hub-channel-grid">
              {content.channels.map(ch => (
                <HubChannelTile key={ch} name={ch} />
              ))}
            </div>
          </article>
        </div>

        <div aria-hidden className="hero-hub-gutter hero-hub-gutter--left" />

        <article className="hub-card hub-card--crm" data-hub-anchor="hub">
          <header className="hub-crm-head">
            <h3 className="hub-crm-title">{content.crmTitle}</h3>
          </header>
          <div className="hub-crm-list">
            {content.customers.map((customer, index) => {
              const icons = statusIcons[index] ?? { status: 'box' as const }
              return (
                <div className="hub-crm-row" key={customer.name}>
                  <div className="hub-crm-row-top">
                    <span className="hub-crm-avatar">
                      <Image
                        alt=""
                        className="hub-crm-avatar-img"
                        height={36}
                        src={HERO_CRM_AVATARS[index % HERO_CRM_AVATARS.length]}
                        width={36}
                      />
                    </span>
                    <div className="hub-crm-meta">
                      <strong className="hub-crm-name">
                        {customer.name}
                        <span aria-hidden className="hub-crm-gender">{GENDER_SYMBOLS[index]}</span>
                      </strong>
                      <span className="hub-crm-phone">{customer.phone}</span>
                    </div>
                    <button aria-label={content.menuAriaLabel} className="hub-crm-more" type="button">
                      <svg aria-hidden className="hub-crm-more-icon" viewBox="0 0 24 24">
                        <circle cx="5" cy="12" r="2" fill="currentColor" />
                        <circle cx="12" cy="12" r="2" fill="currentColor" />
                        <circle cx="19" cy="12" r="2" fill="currentColor" />
                      </svg>
                    </button>
                  </div>
                  <div className="hub-crm-tags">
                    {customer.tags.map(tag => (
                      <span className={hubTagClass(tag)} key={tag}>{tag}</span>
                    ))}
                  </div>
                  {customer.activity && icons.activity && (
                    <p className="hub-crm-status-line">
                      <StatusIcon kind={icons.activity} />
                      <span>{customer.activity}</span>
                    </p>
                  )}
                  <p className="hub-crm-status-line">
                    <StatusIcon kind={icons.status} />
                    <span>{customer.status}</span>
                  </p>
                </div>
              )
            })}
          </div>
        </article>

        <div aria-hidden className="hero-hub-gutter hero-hub-gutter--right" />

        <div className="hero-hub-col hero-hub-col--right">
          <article className="hub-card hub-card--remarketing" data-hub-anchor="remarketing">
            <p className="hub-card-title hub-card-title--compact">{content.remarketingTitle}</p>
            <div className="hub-rm-split">
              <ul className="hub-rm-stats">
                {stats.map(row => (
                  <li className="hub-rm-stat" key={row.label}>
                    <span className="hub-rm-label">{row.label}</span>
                    <span className={`hub-rm-value hub-rm-value--${row.tone ?? 'default'}`}>
                      {row.value}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="hub-rm-pills">
                {content.remarketingPills.map(p => (
                  <span className="hub-rm-pill" key={p.label}>
                    {p.label}
                    {p.isNew && <span className="hub-rm-pill-new">{content.newBadge}</span>}
                  </span>
                ))}
              </div>
            </div>
          </article>

          <article className="hub-card hub-card--security" data-hub-anchor="security">
            <p className="hub-card-title hub-card-title--compact">{content.securityTitle}</p>
            <div className="hub-security-blocks">
              {content.securityPoints.map(point => (
                <p className="hub-security-block" key={point}>{point}</p>
              ))}
            </div>
            <div className="hub-security-lock" aria-hidden>
              <span className="hub-security-lock-icon">
                <svg viewBox="0 0 20 20">
                  <rect fill="currentColor" height="9" rx="2" width="12" x="4" y="9" />
                  <path d="M6.5 9V6.8a3.5 3.5 0 0 1 7 0V9" fill="none" stroke="currentColor" strokeWidth="1.6" />
                </svg>
              </span>
              <span className="hub-security-mask">••••••••</span>
            </div>
          </article>

          <article className="hub-card hub-card--results" data-hub-anchor="results">
            <p className="hub-card-title hub-card-title--compact">{content.resultsTitle}</p>
            <div className="hub-results-body">
              <p className="hub-results-headline">{content.resultsHeadline}</p>
              <div className="hub-results-chart" aria-hidden>
                <div className="hub-results-bars">
                  <div className="hub-results-bar-wrap">
                    <span className="hub-results-bar">
                      <span className="hub-results-bar-fill" style={{ height: '42%' }} />
                    </span>
                    <span className="hub-results-tick">{content.chartPeriod1}</span>
                  </div>
                  <div className="hub-results-bar-wrap">
                    <span className="hub-results-bar hub-results-bar--t2">
                      <span className="hub-results-bar-fill" style={{ height: '88%' }} />
                    </span>
                    <span className="hub-results-tick">{content.chartPeriod2}</span>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
        </div>

        <HubConnectorLines containerRef={gridRef} />
      </div>
    </div>
  )
}
