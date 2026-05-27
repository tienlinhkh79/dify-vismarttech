'use client'
import { RiArrowRightUpLine, RiRobot2Line } from '@remixicon/react'
import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import DifyLogo from '@/app/components/base/logo/dify-logo'
import { APP_DISPLAY_NAME } from '@/config/app-display-name'
import { useGlobalPublicStore } from '@/context/global-public-context'
import { useRouter } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import Avatar from './avatar'

const Header = () => {
  const { t } = useTranslation()
  const router = useRouter()
  const systemFeatures = useGlobalPublicStore(s => s.systemFeatures)

  const goToStudio = useCallback(() => {
    router.push('/apps')
  }, [router])

  return (
    <div
      className={cn(
        'flex w-full gap-3 px-4 py-3',
        'flex-row items-center justify-between',
        'md:flex-col md:items-stretch md:justify-start md:gap-6 md:px-5 md:py-6',
      )}
    >
      <div className="flex min-w-0 items-center gap-3 md:flex-col md:items-start md:gap-4">
        <div className="flex cursor-pointer items-center" onClick={goToStudio}>
          {systemFeatures.branding.enabled && systemFeatures.branding.login_page_logo
            ? (
                <img
                  src={systemFeatures.branding.login_page_logo}
                  className="block h-[22px] w-auto object-contain"
                  alt={`${APP_DISPLAY_NAME} logo`}
                />
              )
            : <DifyLogo />}
        </div>
        <div className="h-4 w-px origin-center rotate-[11.31deg] bg-divider-regular md:hidden" />
        <p className="relative mt-[-2px] truncate title-3xl-semi-bold text-text-primary md:mt-0">
          {t('account.account', { ns: 'common' })}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-3 md:w-full md:flex-col md:items-stretch md:gap-3">
        <Button
          className="gap-2 px-3 py-2 system-sm-medium md:w-full md:justify-center"
          onClick={goToStudio}
        >
          <RiRobot2Line className="h-4 w-4 shrink-0" />
          <p>{t('account.studio', { ns: 'common' })}</p>
          <RiArrowRightUpLine className="h-4 w-4 shrink-0" />
        </Button>
        <div className="h-4 w-px bg-divider-regular md:hidden" />
        <Avatar />
      </div>
    </div>
  )
}
export default Header
