'use client'

import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import Link from '@/next/link'
import { useSearchParams } from '@/next/navigation'

/**
 * Shown when billing_saas redirects here without 9Pay (stub checkout URL).
 * With 9Pay enabled, users go to the payment gateway instead.
 */
export default function BillingCheckoutStubPage() {
  const { t } = useTranslation()
  const searchParams = useSearchParams()
  const plan = searchParams.get('plan') ?? ''
  const interval = searchParams.get('interval') ?? ''
  const selection = useMemo(() => {
    if (!plan && !interval)
      return null
    return [plan, interval].filter(Boolean).join(' · ')
  }, [plan, interval])

  return (
    <div className="flex min-h-[calc(100vh-120px)] justify-center px-6 py-12">
      <div className="flex w-full max-w-lg flex-col gap-6 rounded-xl border border-divider-regular bg-background-default-burn p-8 shadow-sm">
        <div>
          <h1 className="title-lg-semi-bold text-text-primary">
            {t('checkoutStub.title', { ns: 'billing' })}
          </h1>
          <p className="mt-3 system-md-regular text-text-secondary">
            {t('checkoutStub.body', { ns: 'billing' })}
          </p>
          {selection && (
            <p className="mt-4 system-sm-medium text-text-primary">
              {t('checkoutStub.selection', { ns: 'billing', plan, interval })}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button variant="primary" render={<Link href="/apps" />}>
            {t('checkoutStub.backToApps', { ns: 'billing' })}
          </Button>
          <Button variant="secondary" render={<Link href="/account" />}>
            {t('checkoutStub.accountSettings', { ns: 'billing' })}
          </Button>
        </div>
      </div>
    </div>
  )
}
