'use client'

import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import Link from '@/next/link'
import { useSearchParams } from '@/next/navigation'

/**
 * Return landing page after 9Pay redirects the customer back (`return_url`).
 * Set `NINEPAY_RETURN_URL_BASE` on billing_saas to this app URL, e.g.
 * `https://<your-console-host>/billing/9pay-return`
 */
export default function NinepayReturnPage() {
  const { t } = useTranslation()
  const searchParams = useSearchParams()
  const plan = searchParams.get('plan')
  const interval = searchParams.get('interval')

  const planSummary = useMemo(() => {
    if (!plan && !interval)
      return null
    return [plan, interval].filter(Boolean).join(' · ')
  }, [plan, interval])

  return (
    <div className="flex min-h-[calc(100vh-120px)] justify-center px-6 py-12">
      <div className="flex w-full max-w-lg flex-col gap-6 rounded-xl border border-divider-regular bg-background-default-burn p-8 shadow-sm">
        <div>
          <h1 className="title-lg-semi-bold text-text-primary">
            {t('ninepayReturn.title', { ns: 'billing' })}
          </h1>
          <p className="mt-3 system-md-regular text-text-secondary">
            {t('ninepayReturn.description', { ns: 'billing' })}
          </p>
          {planSummary && (
            <p className="mt-2 system-sm-regular text-text-tertiary">
              {planSummary}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button variant="primary" render={<Link href="/apps" />}>
            {t('ninepayReturn.openApps', { ns: 'billing' })}
          </Button>
          <Button variant="secondary" render={<Link href="/account" />}>
            {t('ninepayReturn.openAccount', { ns: 'billing' })}
          </Button>
        </div>
      </div>
    </div>
  )
}
