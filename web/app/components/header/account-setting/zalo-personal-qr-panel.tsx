'use client'

import type { TranslateFn } from './channels-ui'
import { useCallback, useEffect, useRef, useState } from 'react'
import Button from '@/app/components/base/button'
import { toast } from '@/app/components/base/ui/toast'
import { getZaloPersonalLoginStatus, startZaloPersonalLogin } from '@/service/tools'

const POLL_MS = 2000
const TIMEOUT_MS = 600_000

type ZaloPersonalQrPanelProps = {
  channelId: string | null
  active: boolean
  onConnected: () => void
  t: TranslateFn
}

async function resolveStartLoginError(err: unknown, fallback: string): Promise<string> {
  if (err instanceof Response) {
    const data = (await err.json().catch(() => null)) as { error?: string, message?: string } | null
    return data?.message || data?.error || fallback
  }
  if (err instanceof Error && err.message)
    return err.message
  return fallback
}

export default function ZaloPersonalQrPanel({
  channelId,
  active,
  onConnected,
  t,
}: ZaloPersonalQrPanelProps) {
  const [qrDataUri, setQrDataUri] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [retryNonce, setRetryNonce] = useState(0)
  const [connected, setConnected] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const deadlineRef = useRef(0)
  const onConnectedRef = useRef(onConnected)
  const tRef = useRef(t)

  onConnectedRef.current = onConnected
  tRef.current = t

  const clearPoll = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  const retry = useCallback(() => {
    setErrorMessage('')
    setQrDataUri('')
    setRetryNonce(prev => prev + 1)
  }, [])

  useEffect(() => {
    if (!active || !channelId || connected) {
      clearPoll()
      if (!active) {
        queueMicrotask(() => {
          setQrDataUri('')
          setErrorMessage('')
        })
      }
      return
    }

    deadlineRef.current = Date.now() + TIMEOUT_MS

    const pollOnce = async () => {
      if (Date.now() > deadlineRef.current) {
        clearPoll()
        toast.error(tRef.current('settings.channelsZaloPersonalQrTimeout', { ns: 'common' }))
        return
      }
      try {
        const res = await getZaloPersonalLoginStatus(channelId)
        if (res.data?.connected) {
          clearPoll()
          setConnected(true)
          toast.success(tRef.current('settings.channelsZaloPersonalQrSuccess', { ns: 'common' }))
          onConnectedRef.current()
        }
      }
      catch {
        /* ignore transient polling errors */
      }
    }

    const run = async () => {
      setLoading(true)
      setErrorMessage('')
      try {
        const res = await startZaloPersonalLogin(channelId)
        const qr = res.data.qr_data_uri || ''
        if (!qr) {
          const msg = tRef.current('settings.channelsZaloPersonalQrUnavailable', { ns: 'common' })
          setErrorMessage(msg)
          toast.error(msg)
          return
        }
        setQrDataUri(qr)
        intervalRef.current = setInterval(() => {
          void pollOnce()
        }, POLL_MS)
        void pollOnce()
      }
      catch (e: unknown) {
        const msg = await resolveStartLoginError(
          e,
          tRef.current('settings.channelsZaloPersonalQrError', { ns: 'common' }),
        )
        setErrorMessage(msg)
        toast.error(msg)
      }
      finally {
        setLoading(false)
      }
    }

    void run()
    return clearPoll
  }, [active, channelId, connected, retryNonce])

  if (connected) {
    return (
      <div className="rounded-lg border border-divider-subtle bg-state-success-hover px-3 py-2 text-sm text-text-success">
        {t('settings.channelsZaloPersonalQrConnectedInline', { ns: 'common' })}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-lg bg-background-default p-4 ring-1 ring-divider-subtle">
        {loading && !qrDataUri
          ? <span className="text-sm text-text-tertiary">{t('settings.channelsZaloPersonalQrLoading', { ns: 'common' })}</span>
          : qrDataUri
            ? <img src={qrDataUri} alt="Zalo QR" className="max-h-52 w-auto rounded-md" />
            : (
                <>
                  <span className="text-center text-sm text-text-tertiary">
                    {errorMessage || t('settings.channelsZaloPersonalQrUnavailable', { ns: 'common' })}
                  </span>
                  {!!errorMessage && (
                    <Button size="small" variant="secondary" onClick={retry}>
                      {t('settings.channelsZaloPersonalQrRetry', { ns: 'common' })}
                    </Button>
                  )}
                </>
              )}
      </div>
    </div>
  )
}
