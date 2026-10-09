'use client'

import type { MiniCrmBusinessLine, MiniCrmMainTab } from '@/app/components/mini-crm/constants'
import {
  MINI_CRM_BUSINESS_LINES,
  miniCrmTabHref,
  resolveVerticalAndTabFromPathname,
} from '@/app/components/mini-crm/constants'
import {
  RiArrowDownSLine,
  RiBarChartBoxFill,
  RiBarChartBoxLine,
  RiBuilding2Fill,
  RiBuilding2Line,
  RiContactsBookFill,
  RiContactsBookLine,
  RiHandHeartFill,
  RiHandHeartLine,
  RiMegaphoneFill,
  RiMegaphoneLine,
  RiUserSearchFill,
  RiUserSearchLine,
} from '@remixicon/react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { usePathname, useSelectedLayoutSegment } from '@/next/navigation'
import { useMiniCrmAccess } from '@/service/use-common'
import { cn } from '@/utils/classnames'
import { useConsoleNavLayout } from '../console-nav-layout-context'
import {
  cnConsoleSidebarNestedNavItem,
  cnConsoleSidebarRouteNavLink,
} from '../console-nav-sidebar-item-class'

type MiniCrmNavProps = {
  className?: string
}

type SubNavItem = {
  tab: MiniCrmMainTab
  labelKey: 'miniCrm.tabLeads' | 'miniCrm.tabAnalytics' | 'miniCrm.tabRemarketing'
  icon: typeof RiUserSearchLine
  selectedIcon: typeof RiUserSearchFill
}

const SUB_NAV_ITEMS: SubNavItem[] = [
  { tab: 'leads', labelKey: 'miniCrm.tabLeads', icon: RiUserSearchLine, selectedIcon: RiUserSearchFill },
  { tab: 'analytics', labelKey: 'miniCrm.tabAnalytics', icon: RiBarChartBoxLine, selectedIcon: RiBarChartBoxFill },
  { tab: 'remarketing', labelKey: 'miniCrm.tabRemarketing', icon: RiMegaphoneLine, selectedIcon: RiMegaphoneFill },
]

const VERTICAL_CONFIG: Record<MiniCrmBusinessLine, {
  menuKey: 'menus.miniCrmRestaurant' | 'menus.miniCrmNails'
  icon: typeof RiBuilding2Line
  selectedIcon: typeof RiBuilding2Fill
}> = {
  restaurant: {
    menuKey: 'menus.miniCrmRestaurant',
    icon: RiBuilding2Line,
    selectedIcon: RiBuilding2Fill,
  },
  nail: {
    menuKey: 'menus.miniCrmNails',
    icon: RiHandHeartLine,
    selectedIcon: RiHandHeartFill,
  },
}

const nestedChildrenClass = 'flex flex-col gap-0.5 pl-4'

function VerticalNavGroup({
  vertical,
  activated,
  activeBusinessLine,
  activeTab,
}: {
  vertical: MiniCrmBusinessLine
  activated: boolean
  activeBusinessLine: MiniCrmBusinessLine
  activeTab: MiniCrmMainTab
}) {
  const { t } = useTranslation()
  const config = VERTICAL_CONFIG[vertical]
  const isVerticalActive = activated && activeBusinessLine === vertical
  const [expanded, setExpanded] = useState(isVerticalActive)

  useEffect(() => {
    if (isVerticalActive)
      setExpanded(true)
  }, [isVerticalActive])

  const VerticalIcon = isVerticalActive ? config.selectedIcon : config.icon

  return (
    <div className="flex w-full min-w-0 flex-col gap-0.5">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(prev => !prev)}
        className={cnConsoleSidebarNestedNavItem(isVerticalActive)}
      >
        <VerticalIcon className="h-4 w-4 shrink-0" aria-hidden />
        <span className="min-w-0 flex-1 truncate text-left">
          {t(config.menuKey, { ns: 'common' })}
        </span>
        <RiArrowDownSLine
          className={cn('h-4 w-4 shrink-0 transition-transform duration-200', expanded ? 'rotate-0' : '-rotate-90')}
          aria-hidden
        />
      </button>
      {expanded && (
        <div className={nestedChildrenClass}>
          {SUB_NAV_ITEMS.map((item) => {
            const isActive = isVerticalActive && activeTab === item.tab
            const Icon = isActive ? item.selectedIcon : item.icon
            return (
              <Link
                key={item.tab}
                href={miniCrmTabHref(vertical, item.tab)}
                className={cnConsoleSidebarNestedNavItem(isActive)}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-left">
                  {t(item.labelKey, { ns: 'common' })}
                </span>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}

const MiniCrmNav = ({
  className,
}: MiniCrmNavProps) => {
  const { t } = useTranslation()
  const { orientation } = useConsoleNavLayout()
  const isVertical = orientation === 'vertical'
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'mini-crm'
  const pathname = usePathname()
  const { businessLine: activeBusinessLine, mainTab: activeTab } = resolveVerticalAndTabFromPathname(pathname)
  const { data: accessData } = useMiniCrmAccess()
  const [expanded, setExpanded] = useState(activated)

  const accessibleVerticals = useMemo(() => {
    const fromApi = accessData?.data?.verticals || []
    return MINI_CRM_BUSINESS_LINES.filter(line => fromApi.includes(line))
  }, [accessData?.data?.verticals])

  const defaultHref = useMemo(() => {
    const first = accessibleVerticals[0] || 'restaurant'
    return miniCrmTabHref(first, 'leads')
  }, [accessibleVerticals])

  useEffect(() => {
    if (activated)
      setExpanded(true)
  }, [activated])

  if (!isVertical) {
    return (
      <Link
        href={defaultHref}
        className={cnConsoleSidebarRouteNavLink(className, { activated, isVertical })}
      >
        {activated
          ? <RiContactsBookFill className="h-4 w-4 shrink-0" aria-hidden />
          : <RiContactsBookLine className="h-4 w-4 shrink-0" aria-hidden />}
        <span className={cn('ml-2', 'max-[1024px]:hidden')}>
          {t('menus.miniCrm', { ns: 'common' })}
        </span>
      </Link>
    )
  }

  if (!accessibleVerticals.length)
    return null

  return (
    <div className="flex w-full min-w-0 flex-col gap-0.5">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(prev => !prev)}
        className={cnConsoleSidebarRouteNavLink(className, { activated, isVertical })}
      >
        {activated
          ? <RiContactsBookFill className="h-4 w-4 shrink-0" aria-hidden />
          : <RiContactsBookLine className="h-4 w-4 shrink-0" aria-hidden />}
        <span className="min-w-0 flex-1 truncate text-left">
          {t('menus.miniCrm', { ns: 'common' })}
        </span>
        <RiArrowDownSLine
          className={cn('h-4 w-4 shrink-0 transition-transform duration-200', expanded ? 'rotate-0' : '-rotate-90')}
          aria-hidden
        />
      </button>
      {expanded && (
        <div className={nestedChildrenClass}>
          {accessibleVerticals.map(vertical => (
            <VerticalNavGroup
              key={vertical}
              vertical={vertical}
              activated={activated}
              activeBusinessLine={activeBusinessLine}
              activeTab={activeTab}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default MiniCrmNav
