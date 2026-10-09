'use client'

import { miniCrmTabHref } from '@/app/components/mini-crm/constants'
import Loading from '@/app/components/base/loading'
import { useRouter, useSearchParams } from '@/next/navigation'
import { Suspense, useEffect } from 'react'
import { useMiniCrmAccess } from '@/service/use-common'

function MiniCrmIndexRedirect() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { data, isLoading } = useMiniCrmAccess()

  useEffect(() => {
    if (isLoading)
      return
    const verticals = data?.data?.verticals || ['restaurant']
    const targetVertical = verticals.includes('restaurant') ? 'restaurant' : verticals[0]
    const nextParams = new URLSearchParams(searchParams.toString())
    nextParams.delete('tab')
    const query = nextParams.toString()
    router.replace(`${miniCrmTabHref(targetVertical as 'restaurant' | 'nail', 'leads')}${query ? `?${query}` : ''}`)
  }, [data?.data?.verticals, isLoading, router, searchParams])

  return (
    <div className="flex min-h-[50vh] flex-1 items-center justify-center">
      <Loading type="app" />
    </div>
  )
}

export default function MiniCrmIndexPage() {
  return (
    <Suspense
      fallback={(
        <div className="flex min-h-[50vh] flex-1 items-center justify-center">
          <Loading type="app" />
        </div>
      )}
    >
      <MiniCrmIndexRedirect />
    </Suspense>
  )
}
