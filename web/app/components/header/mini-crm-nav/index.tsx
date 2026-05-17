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
        ? <RiContactsBookFill className="h-4 w-4 shrink-0" aria-hidden />
        : <RiContactsBookLine className="h-4 w-4 shrink-0" aria-hidden />}
      <span className={cn(isVertical ? 'min-w-0 flex-1 truncate' : 'ml-2', orientation !== 'vertical' && 'max-[1024px]:hidden')}>
        {t('menus.miniCrm', { ns: 'common' })}
      </span>
    </Link>
  )
}

export default MiniCrmNav
