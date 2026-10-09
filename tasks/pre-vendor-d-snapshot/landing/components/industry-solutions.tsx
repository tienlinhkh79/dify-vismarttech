'use client'

import { useEffect, useState } from 'react'

import { INDUSTRY_PERSON_IMAGES } from '@/content/industry-person-images'
import type { HomeCopy, IndustryId } from '@/content/home-content'

const INDUSTRY_ORDER: IndustryId[] = ['fashion', 'education', 'health', 'restaurants', 'spa']
const MESSAGE_DELAY_MS = 1900
const LOOP_PAUSE_MS = 4200
const INITIAL_DELAY_MS = 450

type IndustrySolutionsProps = {
  content: HomeCopy['industries']
}

function IndustryTabIcon({ id, className }: { id: IndustryId; className?: string }) {
  const common = {
    className,
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    strokeWidth: 1.75,
    viewBox: '0 0 24 24',
    'aria-hidden': true,
  }

  switch (id) {
    case 'fashion':
      return (
        <svg {...common}>
          <path d="M6 3h12l-1.5 4.5H7.5L6 3Z" />
          <path d="M8 7.5 6 21h12l-2-13.5" />
          <path d="M12 7.5v13.5" />
        </svg>
      )
    case 'education':
      return (
        <svg {...common}>
          <path d="M12 3 2 8l10 5 10-5-10-5Z" />
          <path d="M6 10v4.5c0 1.2 2.7 2.5 6 2.5s6-1.3 6-2.5V10" />
          <path d="M20 8v6" />
        </svg>
      )
    case 'health':
      return (
        <svg {...common}>
          <path d="M12 21s-7-4.35-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 11c0 5.65-7 10-7 10Z" />
          <path d="M12 8v6M9 11h6" />
        </svg>
      )
    case 'restaurants':
      return (
        <svg {...common}>
          <path d="M6 3v8a3 3 0 0 0 6 0V3" />
          <path d="M9 11v10" />
          <path d="M18 3v18" />
          <path d="M15 3v5a3 3 0 0 0 6 0V3" />
        </svg>
      )
    case 'spa':
      return (
        <svg {...common}>
          <path d="M12 3c2.5 2.8 5 5.2 5 8.5a5 5 0 1 1-10 0c0-3.3 2.5-5.7 5-8.5Z" />
          <path d="M8.5 14.5 6 21h12l-2.5-6.5" />
        </svg>
      )
  }
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const sync = () => setReduced(media.matches)
    sync()
    media.addEventListener('change', sync)
    return () => media.removeEventListener('change', sync)
  }, [])

  return reduced
}

export default function IndustrySolutions({ content }: IndustrySolutionsProps) {
  const [active, setActive] = useState<IndustryId>('fashion')
  const [visibleCount, setVisibleCount] = useState(0)
  const reducedMotion = usePrefersReducedMotion()
  const industry = content.items[active]
  const messages = industry.messages
  const person = INDUSTRY_PERSON_IMAGES[active]

  const handleTabChange = (id: IndustryId) => {
    setActive(id)
    setVisibleCount(0)
  }

  useEffect(() => {
    if (reducedMotion) {
      setVisibleCount(messages.length)
      return
    }

    setVisibleCount(0)
    let index = 0
    let timer: ReturnType<typeof setTimeout>

    const tick = () => {
      index += 1
      if (index <= messages.length) {
        setVisibleCount(index)
        timer = setTimeout(tick, index === messages.length ? LOOP_PAUSE_MS : MESSAGE_DELAY_MS)
      }
      else {
        index = 0
        setVisibleCount(0)
        timer = setTimeout(tick, MESSAGE_DELAY_MS)
      }
    }

    timer = setTimeout(tick, INITIAL_DELAY_MS)
    return () => clearTimeout(timer)
  }, [active, messages.length, reducedMotion])

  return (
    <section className="industry-solutions" id="industries">
      <div className="container">
        <h2 className="industry-solutions-title text-center">
          {content.titlePrefix}
          {' '}
          <span className="industry-solutions-title-emphasis">{content.titleEmphasis}</span>
        </h2>

        <div className="industry-solutions-card card">
          <div
            aria-label={`${content.titlePrefix} ${content.titleEmphasis}`}
            className="industry-solutions-tabs"
            role="tablist"
          >
            {INDUSTRY_ORDER.map(id => (
              <button
                aria-controls={`industry-panel-${id}`}
                aria-selected={active === id}
                className={`industry-solutions-tab ${active === id ? 'industry-solutions-tab-active' : ''}`}
                id={`industry-tab-${id}`}
                key={id}
                onClick={() => handleTabChange(id)}
                role="tab"
                type="button"
              >
                <IndustryTabIcon className="industry-solutions-tab-icon" id={id} />
                <span>{content.tabs[id]}</span>
              </button>
            ))}
          </div>

          <div
            aria-labelledby={`industry-tab-${active}`}
            className="industry-solutions-body"
            id={`industry-panel-${active}`}
            role="tabpanel"
          >
            <div className="industry-solutions-copy">
              <h3 className="industry-solutions-industry-title">{industry.title}</h3>
              {industry.paragraphs.map(paragraph => (
                <p className="industry-solutions-description" key={paragraph}>{paragraph}</p>
              ))}
              <a className="industry-solutions-cta" href="/signup">
                {content.tryNow}
                <span aria-hidden>›</span>
              </a>
            </div>

            <div className="industry-solutions-demo">
              <div className="industry-solutions-person" aria-hidden="true">
                {/* Native img: static /public assets, no /_next/image (reliable in Docker + nginx). */}
                <img
                  alt=""
                  className="industry-solutions-person-img"
                  decoding="async"
                  key={active}
                  src={person.src}
                />
              </div>

              <div
                aria-label={industry.title}
                aria-live="polite"
                className="industry-solutions-chat"
                role="log"
              >
                {messages.map((message, index) => {
                  const visible = index < visibleCount
                  return (
                    <div
                      className={`industry-solutions-chat-row industry-solutions-chat-${message.role} ${visible ? 'industry-solutions-chat-visible' : ''}`}
                      key={`${active}-${index}-${message.time ?? 'msg'}`}
                    >
                      <div className={`industry-solutions-bubble industry-solutions-bubble-${message.role}`}>
                        <p>{message.text}</p>
                        {message.time && <span className="industry-solutions-time">{message.time}</span>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
