'use client'

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Avatar } from '@/app/components/base/avatar'
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from '@/app/components/base/ui/dropdown-menu'
import { useAppContext } from '@/context/app-context'
import { cn } from '@/utils/classnames'
import AccountAbout from '../account-about'
import { AccountMenuPanel } from './account-menu-panel'

export default function AppSelector({ tone = 'default' }: { tone?: 'default' | 'onPrimary' }) {
  const [aboutVisible, setAboutVisible] = useState(false)
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false)
  const { t } = useTranslation()
  const { userProfile, langGeniusVersionInfo } = useAppContext()

  const isOnPrimary = tone === 'onPrimary'

  return (
    <div>
      <DropdownMenu open={isAccountMenuOpen} onOpenChange={setIsAccountMenuOpen}>
        <DropdownMenuTrigger
          aria-label={t('account.account', { ns: 'common' })}
          className={cn(
            'inline-flex items-center radius-3xl p-0.5',
            isOnPrimary
              ? cn('hover:bg-white/10', isAccountMenuOpen && 'bg-white/10')
              : cn('hover:bg-background-default-dodge', isAccountMenuOpen && 'bg-background-default-dodge'),
          )}
        >
          <Avatar avatar={userProfile.avatar_url} name={userProfile.name} size="lg" />
        </DropdownMenuTrigger>
        <DropdownMenuContent
          sideOffset={6}
          popupClassName="w-60 max-w-80 bg-components-panel-bg-blur! py-0! backdrop-blur-xs"
        >
          <AccountMenuPanel
            closeMenu={() => setIsAccountMenuOpen(false)}
            onRequestAbout={() => {
              setAboutVisible(true)
              setIsAccountMenuOpen(false)
            }}
          />
        </DropdownMenuContent>
      </DropdownMenu>
      {
        aboutVisible && <AccountAbout onCancel={() => setAboutVisible(false)} langGeniusVersionInfo={langGeniusVersionInfo} />
      }
    </div>
  )
}
