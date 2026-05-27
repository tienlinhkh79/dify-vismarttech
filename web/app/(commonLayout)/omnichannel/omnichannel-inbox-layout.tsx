'use client'

import type { ReactNode } from 'react'
import { useTranslation } from '#i18n'
import { RiArrowLeftSLine, RiArrowRightSLine } from '@remixicon/react'
import { useState } from 'react'
import { cn } from '@/utils/classnames'

type OmnichannelInboxLayoutProps = {
  errorBanner: ReactNode
  toolbar: ReactNode
  conversationRail: ReactNode
  conversationMain: ReactNode
  insightRail: ReactNode
}

/**
 * Inbox shell: list / thread (focus) / optional insight panel.
 * Right panel collapses on xl+ to reduce visual weight (Linear-style).
 */
export function OmnichannelInboxLayout({
  errorBanner,
  toolbar,
  conversationRail,
  conversationMain,
  insightRail,
}: OmnichannelInboxLayoutProps) {
  const { t } = useTranslation()
  const [insightOpen, setInsightOpen] = useState(true)

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-background-default">
      {errorBanner}
      {toolbar}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden xl:flex-row">
        {conversationRail}
        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {conversationMain}
        </div>
        <div className="relative z-10 hidden min-h-0 shrink-0 xl:flex">
          <button
            type="button"
            aria-expanded={insightOpen}
            title={insightOpen ? t('settings.omnichannelInsightPanelCollapse') : t('settings.omnichannelInsightPanelExpand')}
            className="flex w-8 shrink-0 flex-col items-center justify-center border-l border-divider-subtle bg-components-panel-bg text-text-quaternary transition-colors hover:bg-state-base-hover hover:text-text-secondary"
            onClick={() => setInsightOpen(v => !v)}
          >
            {insightOpen
              ? <RiArrowRightSLine className="h-4 w-4" aria-hidden />
              : <RiArrowLeftSLine className="h-4 w-4" aria-hidden />}
          </button>
          <div
            className={cn(
              'min-h-0 overflow-hidden border-l border-divider-subtle bg-components-panel-bg transition-[width] duration-200 ease-out',
              insightOpen ? 'w-[min(100vw,300px)]' : 'w-0 border-l-0',
            )}
          >
            <div className="h-full w-[min(100vw,300px)] overflow-y-auto overscroll-y-contain">
              {insightRail}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
