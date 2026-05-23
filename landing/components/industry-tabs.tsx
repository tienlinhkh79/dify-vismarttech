'use client'

import { useState } from 'react'
import type { HomeCopy, IndustryId } from '@/content/home-content'

const INDUSTRY_ORDER: IndustryId[] = ['fashion', 'education', 'health', 'restaurants', 'spa']

type IndustryTabsProps = {
  content: HomeCopy['industries']
}

export default function IndustryTabs({ content }: IndustryTabsProps) {
  const [active, setActive] = useState<IndustryId>('fashion')
  const industry = content.items[active]

  return (
    <section className="container py-12 md:py-16" id="industries">
      <h2 className="section-title text-center">{content.title}</h2>

      <div className="industry-tabs mt-8" role="tablist" aria-label={content.title}>
        {INDUSTRY_ORDER.map(id => (
          <button
            aria-selected={active === id}
            className={`industry-tab ${active === id ? 'industry-tab-active' : ''}`}
            key={id}
            onClick={() => setActive(id)}
            role="tab"
            type="button"
          >
            {content.tabs[id]}
          </button>
        ))}
      </div>

      <div className="industry-panel card mt-6 grid gap-8 p-6 md:grid-cols-2 md:p-8">
        <div>
          <h3 className="text-xl font-bold">{industry.title}</h3>
          <p className="mt-3 text-sm leading-7 text-slate-600">{industry.description}</p>
          <a className="btn btn-primary mt-6" href="/signup">{content.tryNow}</a>
        </div>

        <div className="chat-demo" role="log" aria-label={industry.title}>
          {industry.messages.map((message, index) => (
            <div
              className={`chat-demo-row chat-demo-${message.role}`}
              key={`${message.text}-${index}`}
            >
              {message.role === 'ai' && message.label && (
                <p className="chat-demo-ai-label">{message.label}</p>
              )}
              <div className={`chat-demo-bubble chat-demo-bubble-${message.role}`}>
                <p>{message.text}</p>
                {message.time && <span className="chat-demo-time">{message.time}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
