'use client'

import type { MiniCrmBusinessLine, MiniCrmMainTab } from './constants'
import { useTranslation } from '#i18n'
import Link from '@/next/link'
import { usePathname } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import { miniCrmTabHref, resolveVerticalAndTabFromPathname } from './constants'

const TABS: MiniCrmMainTab[] = ['leads', 'analytics', 'remarketing']

const TAB_LABEL_KEYS: Record<MiniCrmMainTab, 'miniCrm.tabLeads' | 'miniCrm.tabAnalytics' | 'miniCrm.tabRemarketing'> = {
  leads: 'miniCrm.tabLeads',
  analytics: 'miniCrm.tabAnalytics',
  remarketing: 'miniCrm.tabRemarketing',
}

export function MiniCrmMobileSubNav() {
  const { t } = useTranslation('common')
  const pathname = usePathname()
  const { businessLine, mainTab: activeTab } = resolveVerticalAndTabFromPathname(pathname)

  return (
    <div className="flex shrink-0 border-b border-divider-subtle bg-components-panel-bg md:hidden">
      {TABS.map((tab) => {
        const isActive = activeTab === tab
        return (
          <Link
            key={tab}
            href={miniCrmTabHref(businessLine as MiniCrmBusinessLine, tab)}
            className={cn(
              'flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-semibold',
              isActive ? 'text-text-accent' : 'text-text-tertiary',
            )}
          >
            {t(TAB_LABEL_KEYS[tab])}
            {isActive && (
              <span className="h-0.5 w-8 rounded-full bg-text-accent" />
            )}
          </Link>
        )
      })}
    </div>
  )
}
