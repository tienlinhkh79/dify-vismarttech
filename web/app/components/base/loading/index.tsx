'use client'

import { useTranslation } from 'react-i18next'
import LoadingAnim from '@/app/components/base/chat/chat/loading-anim'
import DifyLogo from '@/app/components/base/logo/dify-logo'
import { cn } from '@/utils/classnames'

type ILoadingProps = {
  type?: 'area' | 'app'
  className?: string
}

const Loading = (props?: ILoadingProps) => {
  const { type = 'area', className } = props || {}
  const { t } = useTranslation()

  return (
    <div
      className={cn(
        'flex w-full items-center justify-center',
        type === 'app' && 'h-full flex-col gap-y-4',
        className,
      )}
      role="status"
      aria-live="polite"
      aria-label={t('loading', { ns: 'appApi' })}
    >
      {type === 'app' && <DifyLogo size="large" />}
      <div className="spin-animation">
        <LoadingAnim type="text" />
      </div>
    </div>
  )
}

export default Loading
