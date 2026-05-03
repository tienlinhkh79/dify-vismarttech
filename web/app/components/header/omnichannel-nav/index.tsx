'use client'

import {
  RiCustomerService2Fill,
  RiCustomerService2Line,
} from '@remixicon/react'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { useSelectedLayoutSegment } from '@/next/navigation'
import { cn } from '@/utils/classnames'

type OmnichannelNavProps = {
  className?: string
}

const OmnichannelNav = ({
  className,
}: OmnichannelNavProps) => {
  const { t } = useTranslation()
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'omnichannel'

  return (
    <Link
      href="/omnichannel"
      className={cn(className, 'group', activated && 'bg-components-main-nav-nav-button-bg-active shadow-md', activated ? 'text-components-main-nav-nav-button-text-active' : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover')}
    >
      {activated
        ? <RiCustomerService2Fill className="h-4 w-4 shrink-0" aria-hidden />
        : <RiCustomerService2Line className="h-4 w-4 shrink-0" aria-hidden />}
      <div className="ml-2 max-[1024px]:hidden">
        {t('menus.omnichannel', { ns: 'common' })}
      </div>
    </Link>
  )
}

export default OmnichannelNav
