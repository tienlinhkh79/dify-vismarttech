'use client'

import {
  RiCustomerService2Fill,
  RiCustomerService2Line,
} from '@remixicon/react'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { useSelectedLayoutSegment } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import { useConsoleNavLayout } from '../console-nav-layout-context'
import { cnConsoleSidebarRouteNavLink } from '../console-nav-sidebar-item-class'

type OmnichannelNavProps = {
  className?: string
}

const OmnichannelNav = ({
  className,
}: OmnichannelNavProps) => {
  const { t } = useTranslation()
  const { orientation } = useConsoleNavLayout()
  const isVertical = orientation === 'vertical'
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'omnichannel'

  return (
    <Link
      href="/omnichannel"
      className={cnConsoleSidebarRouteNavLink(className, { activated, isVertical })}
    >
      {activated
        ? <RiCustomerService2Fill className="h-4 w-4 shrink-0" aria-hidden />
        : <RiCustomerService2Line className="h-4 w-4 shrink-0" aria-hidden />}
      <span className={cn(isVertical ? 'min-w-0 flex-1 truncate' : 'ml-2', orientation !== 'vertical' && 'max-[1024px]:hidden')}>
        {t('menus.omnichannel', { ns: 'common' })}
      </span>
    </Link>
  )
}

export default OmnichannelNav
