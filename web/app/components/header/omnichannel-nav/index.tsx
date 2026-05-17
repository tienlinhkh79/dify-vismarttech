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
      className={cn(
        className,
        'group',
        activated && isVertical && "relative border-divider-regular bg-state-base-hover text-text-primary shadow-none before:absolute before:inset-y-2 before:right-2 before:block before:w-[3px] before:rounded-full before:bg-text-accent before:content-['']",
        activated && !isVertical && 'bg-components-main-nav-nav-button-bg-active text-components-main-nav-nav-button-text-active shadow-md',
        !activated && isVertical && 'text-text-secondary hover:bg-state-base-hover hover:text-text-primary',
        !activated && !isVertical && 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover',
      )}
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
