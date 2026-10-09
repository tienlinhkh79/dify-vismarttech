'use client'

import type { MiniCrmBusinessLine, MiniCrmMainTab } from '@/app/components/mini-crm/constants'
import { resolveBusinessLineFromPath, resolveMainTabFromPath } from '@/app/components/mini-crm/constants'
import Loading from '@/app/components/base/loading'
import { useParams, useRouter } from '@/next/navigation'
import { Suspense, useEffect } from 'react'
import MiniCrmPageContent from '../../mini-crm-page-content'

function MiniCrmVerticalTabPageContent() {
  const params = useParams()
  const router = useRouter()
  const rawVertical = typeof params.vertical === 'string' ? params.vertical : 'restaurant'
  const rawTab = typeof params.tab === 'string' ? params.tab : 'leads'
  const businessLine: MiniCrmBusinessLine = resolveBusinessLineFromPath(rawVertical) ?? 'restaurant'
  const mainTab: MiniCrmMainTab = resolveMainTabFromPath(rawTab)

  useEffect(() => {
    if (rawVertical !== businessLine || rawTab !== mainTab)
      router.replace(`/mini-crm/${businessLine}/${mainTab}`)
  }, [businessLine, mainTab, rawTab, rawVertical, router])

  if (rawVertical !== businessLine || rawTab !== mainTab)
    return <Loading type="app" />

  return <MiniCrmPageContent businessLine={businessLine} mainTab={mainTab} />
}

export default function MiniCrmVerticalTabPage() {
  return (
    <Suspense
      fallback={(
        <div className="flex min-h-[50vh] flex-1 items-center justify-center">
          <Loading type="app" />
        </div>
      )}
    >
      <MiniCrmVerticalTabPageContent />
    </Suspense>
  )
}
