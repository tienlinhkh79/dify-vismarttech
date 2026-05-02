'use client'

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
      className={cn('group flex items-center text-sm font-medium', activated && 'hover:bg-components-main-nav-nav-button-bg-active-hover bg-components-main-nav-nav-button-bg-active font-semibold shadow-md', activated ? 'text-components-main-nav-nav-button-text-active' : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover', className)}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', activated ? 'bg-primary-600' : 'bg-text-tertiary')} />
      <div className="ml-2 max-[1024px]:hidden">
        {t('menus.omnichannel', { ns: 'common' })}
      </div>
    </Link>
  )
}

export default OmnichannelNav
