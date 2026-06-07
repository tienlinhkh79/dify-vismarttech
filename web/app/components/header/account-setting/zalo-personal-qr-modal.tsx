'use client'

import type { TranslateFn } from './channels-ui'
import Button from '@/app/components/base/button'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogTitle,
} from '@/app/components/base/ui/dialog'
import ZaloPersonalQrPanel from './zalo-personal-qr-panel'

type ZaloPersonalQrModalProps = {
  channelId: string | null
  open: boolean
  onClose: () => void
  onConnected: () => void
  t: TranslateFn
}

export default function ZaloPersonalQrModal({
  channelId,
  open,
  onClose,
  onConnected,
  t,
}: ZaloPersonalQrModalProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v)
          onClose()
      }}
    >
      <DialogContent className="max-w-md">
        <DialogTitle>{t('settings.channelsZaloPersonalQrTitle', { ns: 'common' })}</DialogTitle>
        <DialogCloseButton />
        <ZaloPersonalQrPanel
          channelId={channelId}
          active={open}
          onConnected={onConnected}
          t={t}
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>{t('operation.cancel', { ns: 'common' })}</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
