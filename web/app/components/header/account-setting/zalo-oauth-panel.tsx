'use client'

import type { TranslateFn } from './channels-ui'
import { useEffect, useRef, useState } from 'react'
import Button from '@/app/components/base/button'
import { toast } from '@/app/components/base/ui/toast'
import { getZaloChannelOAuthStatus, startZaloChannelOAuth } from '@/service/tools'

const POLL_MS = 2000
const TIMEOUT_MS = 600_000

type ZaloOAuthPanelMeta = {
  oauth_callback_url: string
}

type ZaloOAuthPanelProps = {
  channelId: string | null
  active: boolean
  onConnected: () => void
  onStarted?: (meta: ZaloOAuthPanelMeta) => void
  t: TranslateFn
}

export default function ZaloOAuthPanel({
  channelId,
  active,
  onConnected,
  onStarted,
  t,
}: ZaloOAuthPanelProps) {
  const [qrDataUri, setQrDataUri] = useState('')
  const [authUrl, setAuthUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [connected, setConnected] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const deadlineRef = useRef(0)
  const onConnectedRef = useRef(onConnected)
  const onStartedRef = useRef(onStarted)
  const tRef = useRef(t)

  onConnectedRef.current = onConnected
  onStartedRef.current = onStarted
  tRef.current = t

  const clearPoll = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  useEffect(() => {
    if (!active || !channelId || connected) {
      clearPoll()
      if (!active) {
        queueMicrotask(() => {
          setQrDataUri('')
          setAuthUrl('')
        })
      }
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
          setConnected(true)
          toast.success(tRef.current('settings.channelsZaloOAuthSuccess', { ns: 'common' }))
          onConnectedRef.current()
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
        setQrDataUri(data.qr_data_uri || '')
        setAuthUrl(data.auth_url || '')
        if (data.oauth_callback_url)
          onStartedRef.current?.({ oauth_callback_url: data.oauth_callback_url })
        intervalRef.current = setInterval(() => {
          void pollOnce()
        }, POLL_MS)
        void pollOnce()
      }
      catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e)
        toast.error(msg || tRef.current('settings.channelsZaloOAuthStartError', { ns: 'common' }))
      }
      finally {
        setLoading(false)
      }
    }

    void run()
    return clearPoll
  }, [active, channelId, connected])

  if (connected) {
    return (
      <div className="rounded-lg border border-divider-subtle bg-state-success-hover px-3 py-2 text-sm text-text-success">
        {t('settings.channelsZaloOaOAuthConnectedInline', { ns: 'common' })}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-3">
      {loading && (
        <div className="system-sm-regular text-text-tertiary">
          {t('settings.channelsZaloOAuthLoading', { ns: 'common' })}
        </div>
      )}
      {!loading && qrDataUri && (
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
    </div>
  )
}
