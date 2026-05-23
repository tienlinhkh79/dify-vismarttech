'use client'

import Image from 'next/image'

import { HubChannelTile } from '@/components/brand-icons'
import { HERO_CHAT_PRODUCT_IMAGE } from '@/content/module-placeholders'
import type { HomeCopy } from '@/content/home-content'

type HeroShowcaseProps = {
  content: HomeCopy['hero']['showcase']
}

const RM_VALUES = { total: 454, viewed: 312, clicked: 100, failed: 0 } as const

type RemarketingStatRow = { label: string; value: number; muted?: boolean }

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

export default function HeroShowcase({ content }: HeroShowcaseProps) {
  const rm = content.remarketing
  const stats: RemarketingStatRow[] = [
    { label: rm.total, value: RM_VALUES.total },
    { label: rm.viewed, value: RM_VALUES.viewed },
    { label: rm.clicked, value: RM_VALUES.clicked },
    { label: rm.failed, value: RM_VALUES.failed, muted: true },
  ]
  const max = RM_VALUES.total

  return (
    <div className="hero-hub">
      <div aria-hidden className="hero-hub-glow" />

      <div className="hero-hub-grid">
        <div className="hero-hub-col hero-hub-col--left">
          <article className="hub-card hub-card--chat">
            <p className="hub-card-kicker">
              {content.chatTitle}
              <span className="hub-card-kicker-muted"> · {content.chatShop}</span>
            </p>
            <div className="hub-chat-body">
              <div className="hub-chat-product">
                <Image
                  alt=""
                  className="hub-chat-product-img"
                  height={140}
                  src={HERO_CHAT_PRODUCT_IMAGE}
                  width={112}
                />
              </div>
              <div className="hub-chat-thread">
                <div className="hub-bubble hub-bubble--user">{content.chatQuestion}</div>
                <div className="hub-bubble hub-bubble--ai">{content.chatAnswer}</div>
              </div>
            </div>
          </article>

          <article className="hub-card hub-card--channels">
            <p className="hub-card-kicker">{content.channelsTitle}</p>
            <div className="hub-channel-grid">
              {content.channels.map(ch => (
                <HubChannelTile key={ch} name={ch} />
              ))}
            </div>
          </article>
        </div>

        <div aria-hidden className="hero-hub-connector hero-hub-connector--left" />

        <article className="hub-card hub-card--crm">
          <div className="hub-crm-head">
            <h3 className="hub-crm-title">{content.crmTitle}</h3>
          </div>
          <div className="hub-crm-list">
            {content.customers.map(customer => (
              <div className="hub-crm-row" key={customer.name}>
                <div className="hub-crm-row-top">
                  <span className="hub-crm-avatar" aria-hidden>{customer.name.charAt(0)}</span>
                  <div className="hub-crm-meta">
                    <strong className="hub-crm-name">{customer.name}</strong>
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
                {customer.activity && (
                  <p className="hub-crm-activity">
                    <span aria-hidden className="hub-crm-activity-icon">✓</span>
                    {customer.activity}
                  </p>
                )}
                <p className="hub-crm-status">{customer.status}</p>
              </div>
            ))}
          </div>
        </article>

        <div aria-hidden className="hero-hub-connector hero-hub-connector--right" />

        <div className="hero-hub-col hero-hub-col--right">
          <article className="hub-card hub-card--remarketing">
            <p className="hub-card-kicker">{content.remarketingTitle}</p>
            <div className="hub-rm-stats">
              {stats.map(row => (
                <div className="hub-rm-stat" key={row.label}>
                  <div className="hub-rm-stat-top">
                    <span className="hub-rm-label">{row.label}</span>
                    <span className={`hub-rm-value ${row.muted ? 'hub-rm-value--muted' : ''}`}>
                      {row.value}
                    </span>
                  </div>
                  <div className="hub-rm-track">
                    <span
                      className={`hub-rm-fill ${row.muted ? 'hub-rm-fill--muted' : ''}`}
                      style={{ width: `${max ? (row.value / max) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="hub-rm-pills">
              {content.remarketingPills.map(p => (
                <span className="hub-rm-pill" key={p.label}>
                  {p.label}
                  {p.isNew && <span className="hub-rm-pill-new">{content.newBadge}</span>}
                </span>
              ))}
            </div>
          </article>

          <article className="hub-card hub-card--security">
            <p className="hub-card-kicker">{content.securityTitle}</p>
            <ul className="hub-security-list">
              {content.securityPoints.map(point => (
                <li key={point}>{point}</li>
              ))}
            </ul>
            <div className="hub-security-lock" aria-hidden>
              <span className="hub-security-emoji">🔒</span>
              <span className="hub-security-mask">••••••••</span>
            </div>
          </article>

          <article className="hub-card hub-card--results">
            <p className="hub-card-kicker">{content.resultsTitle}</p>
            <div className="hub-results-body">
              <div className="hub-results-chart" aria-hidden>
                <div className="hub-results-bars">
                  <div className="hub-results-bar-wrap">
                    <span className="hub-results-bar" style={{ height: '42%' }} />
                    <span className="hub-results-tick">{content.chartPeriod1}</span>
                  </div>
                  <div className="hub-results-bar-wrap">
                    <span className="hub-results-bar hub-results-bar--t2" style={{ height: '88%' }} />
                    <span className="hub-results-tick">{content.chartPeriod2}</span>
                  </div>
                </div>
              </div>
              <p className="hub-results-headline">{content.resultsHeadline}</p>
            </div>
          </article>
        </div>
      </div>
    </div>
  )
}
