'use client'

import type { TranslateFn } from './channels-ui'
import { useEffect, useRef, useState } from 'react'
import Button from '@/app/components/base/button'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogTitle,
} from '@/app/components/base/ui/dialog'
import { toast } from '@/app/components/base/ui/toast'
import { getZaloChannelOAuthStatus, startZaloChannelOAuth } from '@/service/tools'

type ZaloOAuthModalProps = {
  channelId: string | null
  open: boolean
  onClose: () => void
  onConnected: () => void
  t: TranslateFn
}

const POLL_MS = 2000
const TIMEOUT_MS = 600_000

export default function ZaloOAuthModal({
  channelId,
  open,
  onClose,
  onConnected,
  t,
}: ZaloOAuthModalProps) {
  const [qrDataUri, setQrDataUri] = useState('')
  const [authUrl, setAuthUrl] = useState('')
  const [callbackUrl, setCallbackUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const deadlineRef = useRef(0)
  const onConnectedRef = useRef(onConnected)
  const onCloseRef = useRef(onClose)
  const tRef = useRef(t)

  onConnectedRef.current = onConnected
  onCloseRef.current = onClose
  tRef.current = t

  const clearPoll = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  useEffect(() => {
    if (!open || !channelId) {
      clearPoll()
      setQrDataUri('')
      setAuthUrl('')
      setCallbackUrl('')
      return
    }

    deadlineRef.current = Date.now() + TIMEOUT_MS

    const pollOnce = async () => {
      if (Date.now() > deadlineRef.current) {
        clearPoll()
        toast.error(tRef.current('settings.channelsZaloOAuthTimeout', { ns: 'common' }))
        return
      }
      try {
        const res = await getZaloChannelOAuthStatus(channelId)
        if (res.data?.connected) {
          clearPoll()
          toast.success(tRef.current('settings.channelsZaloOAuthSuccess', { ns: 'common' }))
          onConnectedRef.current()
          onCloseRef.current()
        }
      }
      catch {
        /* ignore transient polling errors */
      }
    }

    const run = async () => {
      setLoading(true)
      try {
        const res = await startZaloChannelOAuth(channelId)
        const data = res.data
        setQrDataUri(data.qr_data_uri)
        setAuthUrl(data.auth_url)
        setCallbackUrl(data.oauth_callback_url)
        intervalRef.current = setInterval(() => {
          void pollOnce()
        }, POLL_MS)
        void pollOnce()
      }
      catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e)
        toast.error(msg || tRef.current('settings.channelsZaloOAuthStartError', { ns: 'common' }))
        onCloseRef.current()
      }
      finally {
        setLoading(false)
      }
    }

    void run()

    return () => {
      clearPoll()
    }
  }, [open, channelId])

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      clearPoll()
      onClose()
    }
  }

  const copyText = async (value: string, okKey: string) => {
    if (!value)
      return
    try {
      await navigator.clipboard.writeText(value)
      toast.success(t(okKey, { ns: 'common' }))
    }
    catch {
      toast.error(t('settings.channelsCopyFailed', { ns: 'common' }))
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="w-[440px] max-w-[440px] overflow-hidden p-0">
        <DialogCloseButton className="right-5 top-5" />
        <div className="px-6 pb-3 pr-14 pt-6">
          <DialogTitle className="text-text-primary title-lg-semi-bold">
            {t('settings.channelsZaloQRTitle', { ns: 'common' })}
          </DialogTitle>
          <p className="mt-2 system-sm-regular text-text-secondary">
            {t('settings.channelsZaloQRHint', { ns: 'common' })}
          </p>
        </div>
        <div className="flex flex-col items-center gap-3 px-6 pb-6">
          {loading && (
            <div className="system-sm-regular text-text-tertiary">
              {t('settings.channelsZaloOAuthLoading', { ns: 'common' })}
            </div>
          )}
          {!loading && qrDataUri && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={qrDataUri} alt="" className="size-56 rounded-lg border border-divider-subtle bg-white p-2" />
          )}
          {authUrl && (
            <Button
              variant="primary"
              className="w-full"
              onClick={() => window.open(authUrl, '_blank', 'noopener,noreferrer')}
            >
              {t('settings.channelsZaloOpenAuthLink', { ns: 'common' })}
            </Button>
          )}
          {callbackUrl && (
            <div className="w-full space-y-1 rounded-lg border border-divider-subtle bg-background-default px-3 py-2">
              <div className="system-xs-semibold-uppercase text-text-tertiary">
                {t('settings.channelsZaloCallbackUrlLabel', { ns: 'common' })}
              </div>
              <div className="break-all system-xs-regular text-text-secondary">{callbackUrl}</div>
              <Button size="small" variant="secondary" onClick={() => copyText(callbackUrl, 'settings.channelsCopyWebhookUrlSuccess')}>
                {t('operation.copy', { ns: 'common' })}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
