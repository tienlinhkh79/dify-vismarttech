'use client'

import type { TranslateFn } from './channels-ui'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogTitle,
} from '@/app/components/base/ui/dialog'
import ZaloOAuthPanel from './zalo-oauth-panel'

type ZaloOAuthModalProps = {
  channelId: string | null
  open: boolean
  onClose: () => void
  onConnected: () => void
  t: TranslateFn
}

export default function ZaloOAuthModal({
  channelId,
  open,
  onClose,
  onConnected,
  t,
}: ZaloOAuthModalProps) {
  const handleOpenChange = (next: boolean) => {
    if (!next)
      onClose()
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="w-[440px] max-w-[440px] overflow-hidden p-0">
        <DialogCloseButton className="top-5 right-5" />
        <div className="px-6 pt-6 pr-14 pb-3">
          <DialogTitle className="title-lg-semi-bold text-text-primary">
            {t('settings.channelsZaloQRTitle', { ns: 'common' })}
          </DialogTitle>
          <p className="mt-2 system-sm-regular text-text-secondary">
            {t('settings.channelsZaloQRHint', { ns: 'common' })}
          </p>
        </div>
        <div className="px-6 pb-6">
          <ZaloOAuthPanel
            channelId={channelId}
            active={open}
            onConnected={() => {
              onConnected()
              onClose()
            }}
            t={t}
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}
