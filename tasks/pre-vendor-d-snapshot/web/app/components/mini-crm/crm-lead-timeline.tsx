'use client'

import type { MiniCrmTimelineItem } from '@/service/tools'
import { useTranslation } from '#i18n'
import { useCallback, useEffect, useState } from 'react'
import Loading from '@/app/components/base/loading'
import { listMiniCrmLeadTimeline } from '@/service/tools'

type CrmLeadTimelineProps = {
  conversationId: string
}

export function CrmLeadTimeline({ conversationId }: CrmLeadTimelineProps) {
  const { t } = useTranslation('common')
  const [items, setItems] = useState<MiniCrmTimelineItem[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const loadTimeline = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await listMiniCrmLeadTimeline(conversationId)
      setItems((response.data || []).filter(item => item.kind === 'activity'))
    }
    catch {
      setItems([])
    }
    finally {
      setIsLoading(false)
    }
  }, [conversationId])

  useEffect(() => {
    void loadTimeline()
  }, [loadTimeline])

  const resolveLabel = (item: MiniCrmTimelineItem) => {
    const typeLabels: Record<string, string> = {
      stage_changed: t('miniCrm.timelineStageChanged'),
      notes_updated: t('miniCrm.timelineNotesUpdated'),
      notes_appended: t('miniCrm.timelineNotesAppended'),
      owner_changed: t('miniCrm.timelineOwnerChanged'),
      tags_updated: t('miniCrm.timelineTagsUpdated'),
      source_updated: t('miniCrm.timelineSourceUpdated'),
      contact_updated: t('miniCrm.timelineContactUpdated'),
      auto_qualified: t('miniCrm.timelineAutoQualified'),
    }
    return typeLabels[item.activity_type] || item.activity_type
  }

  if (isLoading && !items.length) {
    return (
      <div className="flex min-h-[4rem] items-center justify-center">
        <Loading type="area" />
      </div>
    )
  }

  if (!items.length) {
    return <p className="text-xs text-text-tertiary">{t('miniCrm.timelineEmpty')}</p>
  }

  return (
    <ul className="space-y-2">
      {items.map(item => (
        <li
          key={`${item.kind}-${item.id}`}
          className="flex items-start gap-3 rounded-lg border border-divider-subtle bg-background-default-subtle px-3 py-2"
        >
          <div className="mt-1 size-1.5 shrink-0 rounded-full bg-util-colors-blue-brand-blue-brand-600" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-text-secondary">{resolveLabel(item)}</span>
              <span className="shrink-0 text-[10px] text-text-quaternary tabular-nums">
                {item.at ? new Date(item.at).toLocaleString() : '-'}
              </span>
            </div>
            <div className="mt-0.5 text-xs text-text-primary">{item.summary}</div>
          </div>
        </li>
      ))}
    </ul>
  )
}
