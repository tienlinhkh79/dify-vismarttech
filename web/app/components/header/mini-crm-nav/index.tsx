'use client'

import {
  RiContactsBookFill,
  RiContactsBookLine,
} from '@remixicon/react'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { useSelectedLayoutSegment } from '@/next/navigation'
import { cn } from '@/utils/classnames'

type MiniCrmNavProps = {
  className?: string
}

const MiniCrmNav = ({
  className,
}: MiniCrmNavProps) => {
  const { t } = useTranslation()
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'mini-crm'

  return (
    <Link
      href="/mini-crm"
      className={cn(className, 'group', activated && 'bg-components-main-nav-nav-button-bg-active shadow-md', activated ? 'text-components-main-nav-nav-button-text-active' : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover')}
    >
      {activated
        ? <RiContactsBookFill className="h-4 w-4 shrink-0" aria-hidden />
        : <RiContactsBookLine className="h-4 w-4 shrink-0" aria-hidden />}
      <div className="ml-2 max-[1024px]:hidden">
        {t('menus.miniCrm', { ns: 'common' })}
      </div>
    </Link>
  )
}

export default MiniCrmNav
