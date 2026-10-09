'use client'

import Loading from '@/app/components/base/loading'
import { useRouter, useSearchParams } from '@/next/navigation'
import { Suspense, useEffect } from 'react'

function LegacyMiniCrmTabRedirect({ tab }: { tab: 'leads' | 'analytics' | 'remarketing' }) {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams.toString())
    const query = nextParams.toString()
    router.replace(`/mini-crm/restaurant/${tab}${query ? `?${query}` : ''}`)
  }, [router, searchParams, tab])

  return (
    <div className="flex min-h-[50vh] flex-1 items-center justify-center">
      <Loading type="app" />
    </div>
  )
}

function LegacyRemarketingRedirect() {
  return <LegacyMiniCrmTabRedirect tab="remarketing" />
}

export default function MiniCrmLegacyRemarketingPage() {
  return (
    <Suspense
      fallback={(
        <div className="flex min-h-[50vh] flex-1 items-center justify-center">
          <Loading type="app" />
        </div>
      )}
    >
      <LegacyRemarketingRedirect />
    </Suspense>
  )
}
