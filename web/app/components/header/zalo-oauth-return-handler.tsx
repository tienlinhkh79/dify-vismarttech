'use client'

import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from '@/app/components/base/ui/toast'

/**
 * Clears Zalo OAuth query params after redirect and surfaces result toasts.
 */
export default function ZaloOAuthReturnHandler() {
  const { t } = useTranslation()

  useEffect(() => {
    if (typeof window === 'undefined')
      return
    const params = new URLSearchParams(window.location.search)
    const zalo = params.get('zalo_oauth')
    if (!zalo)
      return

    const reasonRaw = (params.get('reason') || '').trim()
    const knownReason = new Set([
      'missing_state',
      'expired_state',
      'missing_code',
      'channel_not_found',
      'oauth_callback_error',
    ])
    const reasonKey = knownReason.has(reasonRaw) ? `settings.channelsZaloOAuthReason.${reasonRaw}` : ''
    const reasonText = reasonKey ? t(reasonKey, { ns: 'common' }) : reasonRaw
    const reasonSuffix = reasonText ? `: ${reasonText}` : ''
    if (zalo === 'success')
      toast.success(t('settings.channelsZaloOAuthToastSuccess', { ns: 'common' }))
    else
      toast.error(t('settings.channelsZaloOAuthToastError', { ns: 'common', reason: reasonSuffix }))

    params.delete('zalo_oauth')
    params.delete('reason')
    params.delete('channel_id')
    const qs = params.toString()
    const next = `${window.location.pathname}${qs ? `?${qs}` : ''}${window.location.hash}`
    window.history.replaceState({}, '', next)
  }, [t])

  return null
}
