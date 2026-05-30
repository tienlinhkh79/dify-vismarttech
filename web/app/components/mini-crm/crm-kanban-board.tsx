'use client'

import type { MiniCrmStage } from './constants'
import type { MiniCrmLeadRow } from '@/service/tools'
import { useTranslation } from '#i18n'
import { useMemo, useState } from 'react'
import { toast } from '@/app/components/base/ui/toast'
import Link from '@/next/link'
import { patchMiniCrmLead } from '@/service/tools'
import { cn } from '@/utils/classnames'
import { MINI_CRM_STAGES } from './constants'
import { CrmLeadTags } from './crm-lead-tags'
import { StageTag } from './stage-tag'

type CrmKanbanBoardProps = {
  leadRows: MiniCrmLeadRow[]
  isLoading: boolean
  resolveStageLabel: (stage: string) => string
  resolveChannelLabel: (channelType: string) => string
  onLeadUpdated: (leadRow: MiniCrmLeadRow) => void
}

export function CrmKanbanBoard({
  leadRows,
  isLoading,
  resolveStageLabel,
  resolveChannelLabel,
  onLeadUpdated,
}: CrmKanbanBoardProps) {
  const { t } = useTranslation('common')
  const [draggingConversationId, setDraggingConversationId] = useState<string | null>(null)
  const [dropTargetStage, setDropTargetStage] = useState<string | null>(null)

  const leadsByStage = useMemo(() => {
    const grouped: Record<MiniCrmStage, MiniCrmLeadRow[]> = {
      new: [],
      qualified: [],
      won: [],
      lost: [],
    }
    for (const leadRow of leadRows) {
      const stage = (MINI_CRM_STAGES.includes(leadRow.stage as MiniCrmStage)
        ? leadRow.stage
        : 'new') as MiniCrmStage
      grouped[stage].push(leadRow)
    }
    return grouped
  }, [leadRows])

  const handleDrop = async (stage: MiniCrmStage) => {
    const conversationId = draggingConversationId
    setDropTargetStage(null)
    setDraggingConversationId(null)
    if (!conversationId)
      return
    const leadRow = leadRows.find(row => row.conversation_id === conversationId)
    if (!leadRow || leadRow.stage === stage)
      return
    try {
      const response = await patchMiniCrmLead(conversationId, { stage })
      onLeadUpdated(response.data)
      toast.success(t('miniCrm.saveSuccess'))
    }
    catch {
      toast.error(t('miniCrm.errorSave'))
    }
  }

  return (
    <div className="grid gap-3 xl:grid-cols-4">
      {MINI_CRM_STAGES.map((stage) => {
        const columnLeads = leadsByStage[stage]
        const isDropTarget = dropTargetStage === stage
        return (
          <div
            key={stage}
            className={cn(
              'flex min-h-[320px] flex-col rounded-xl border border-divider-regular bg-background-default-subtle',
              isDropTarget && 'ring-2 ring-components-panel-border',
            )}
            onDragOver={(e) => {
              e.preventDefault()
              setDropTargetStage(stage)
            }}
            onDragLeave={() => {
              if (dropTargetStage === stage)
                setDropTargetStage(null)
            }}
            onDrop={(e) => {
              e.preventDefault()
              void handleDrop(stage)
            }}
          >
            <div className="flex items-center justify-between border-b border-divider-subtle px-3 py-2">
              <StageTag stage={stage} />
              <span className="text-xs text-text-tertiary tabular-nums">{columnLeads.length}</span>
            </div>
            <div className="flex-1 space-y-2 overflow-y-auto p-2">
              {isLoading && !columnLeads.length && (
                <div className="px-2 py-4 text-center text-xs text-text-tertiary">…</div>
              )}
              {columnLeads.map((leadRow) => {
                const contactName = (leadRow.participant_display_name || '').trim() || leadRow.external_user_id
                return (
                  <div
                    key={leadRow.conversation_id}
                    draggable
                    onDragStart={() => setDraggingConversationId(leadRow.conversation_id)}
                    onDragEnd={() => {
                      setDraggingConversationId(null)
                      setDropTargetStage(null)
                    }}
                    className={cn(
                      'cursor-grab rounded-lg border border-divider-regular bg-background-default p-3 shadow-sm active:cursor-grabbing',
                      draggingConversationId === leadRow.conversation_id && 'opacity-60',
                    )}
                  >
                    <div className="font-medium text-text-primary">{contactName}</div>
                    <div className="mt-1 text-xs text-text-tertiary">
                      {resolveChannelLabel(leadRow.channel_type)}
                    </div>
                    <CrmLeadTags tags={leadRow.tags} className="mt-2" />
                    {(leadRow.contact_phone || leadRow.contact_email) && (
                      <div className="mt-2 space-y-0.5 text-xs text-text-secondary">
                        {leadRow.contact_phone && <div>{leadRow.contact_phone}</div>}
                        {leadRow.contact_email && <div className="truncate">{leadRow.contact_email}</div>}
                      </div>
                    )}
                    <div className="mt-3 flex items-center justify-between gap-2">
                      <span className="text-[10px] text-text-quaternary uppercase">{resolveStageLabel(stage)}</span>
                      <Link
                        href={`/omnichannel?channel_id=${encodeURIComponent(leadRow.channel_id)}&conversation_id=${encodeURIComponent(leadRow.conversation_id)}`}
                        className="text-xs font-medium text-text-accent"
                      >
                        {t('miniCrm.openInbox')}
                      </Link>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
