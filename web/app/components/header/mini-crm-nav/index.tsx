'use client'

import {
  RiContactsBookFill,
  RiContactsBookLine,
} from '@remixicon/react'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { useSelectedLayoutSegment } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import { useConsoleNavLayout } from '../console-nav-layout-context'
import { cnConsoleSidebarRouteNavLink } from '../console-nav-sidebar-item-class'

type MiniCrmNavProps = {
  className?: string
}

const MiniCrmNav = ({
  className,
}: MiniCrmNavProps) => {
  const { t } = useTranslation()
  const { orientation } = useConsoleNavLayout()
  const isVertical = orientation === 'vertical'
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'mini-crm'

  return (
    <Link
      href="/mini-crm"
      className={cnConsoleSidebarRouteNavLink(className, { activated, isVertical })}
    >
      {activated
        ? <RiContactsBookFill className="h-4 w-4 shrink-0" aria-hidden />
        : <RiContactsBookLine className="h-4 w-4 shrink-0" aria-hidden />}
      <span className={cn(isVertical ? 'min-w-0 flex-1 truncate' : 'ml-2', orientation !== 'vertical' && 'max-[1024px]:hidden')}>
        {t('menus.miniCrm', { ns: 'common' })}
      </span>
    </Link>
  )
}

export default MiniCrmNav
