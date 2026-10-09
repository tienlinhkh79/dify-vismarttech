'use client'

import type { MiniCrmStage } from './constants'
import type { MiniCrmLeadRow } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiExternalLinkLine } from '@remixicon/react'
import { useMemo, useState } from 'react'
import { toast } from '@/app/components/base/ui/toast'
import Link from '@/next/link'
import { patchMiniCrmLead } from '@/service/tools'
import { cn } from '@/utils/classnames'
import { MINI_CRM_STAGES } from './constants'
import { CRM_BRAND } from './crm-theme'
import { CrmContactAvatar } from './crm-contact-avatar'
import { resolveStageTheme } from './crm-theme'
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
    <div className="grid gap-4 xl:grid-cols-4">
      {MINI_CRM_STAGES.map((stage) => {
        const columnLeads = leadsByStage[stage]
        const theme = resolveStageTheme(stage)
        const isDropTarget = dropTargetStage === stage
        return (
          <div
            key={stage}
            className={cn(
              'flex min-h-[360px] flex-col overflow-hidden rounded-lg border transition-all',
              isDropTarget && 'scale-[1.01] shadow-lg',
            )}
              style={{
                borderColor: isDropTarget ? theme.color : CRM_BRAND.border,
                backgroundColor: CRM_BRAND.headerBg,
              }}
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
            <div
              className="flex items-center justify-between border-b px-4 py-3"
              style={{ backgroundColor: theme.bgColor, borderColor: CRM_BRAND.border }}
            >
              <div className="flex items-center gap-2">
                <div
                  className="size-2.5 rounded-full"
                  style={{ backgroundColor: theme.color }}
                />
                <StageTag stage={stage} />
              </div>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums"
                style={{ backgroundColor: theme.bgColor, color: theme.color }}
              >
                {columnLeads.length}
              </span>
            </div>
            <div className="flex-1 space-y-2.5 overflow-y-auto p-3">
              {isLoading && !columnLeads.length && (
                <div className="px-2 py-6 text-center text-xs text-text-tertiary">…</div>
              )}
              {!isLoading && !columnLeads.length && (
                <div
                  className="rounded-lg border border-dashed px-3 py-8 text-center text-xs"
                  style={{ borderColor: CRM_BRAND.borderStrong, color: CRM_BRAND.textMuted }}
                >
                  {resolveStageLabel(stage)}
                </div>
              )}
              {columnLeads.map((leadRow) => {
                const contactName = (leadRow.participant_display_name || '').trim() || leadRow.external_user_id
                const isDragging = draggingConversationId === leadRow.conversation_id
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
                      'cursor-grab rounded-lg border p-3 transition-all active:cursor-grabbing',
                      'hover:shadow-md',
                      isDragging && 'scale-95 opacity-50',
                    )}
                    style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
                  >
                    <div className="flex items-start gap-2.5">
                      <CrmContactAvatar name={contactName} stage={leadRow.stage} size="sm" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium" style={{ color: CRM_BRAND.textPrimary }}>{contactName}</div>
                        <div className="mt-0.5 text-xs" style={{ color: CRM_BRAND.textMuted }}>
                          {resolveChannelLabel(leadRow.channel_type)}
                        </div>
                      </div>
                    </div>
                    <CrmLeadTags tags={leadRow.tags} className="mt-2.5" />
                    {(leadRow.contact_phone || leadRow.contact_email) && (
                      <div className="mt-2 space-y-0.5 text-xs" style={{ color: CRM_BRAND.textSecondary }}>
                        {leadRow.contact_phone && <div>{leadRow.contact_phone}</div>}
                        {leadRow.contact_email && <div className="truncate">{leadRow.contact_email}</div>}
                      </div>
                    )}
                    <div className="mt-3 flex items-center justify-end border-t pt-2.5" style={{ borderColor: CRM_BRAND.border }}>
                      <Link
                        href={`/omnichannel?channel_id=${encodeURIComponent(leadRow.channel_id)}&conversation_id=${encodeURIComponent(leadRow.conversation_id)}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold hover:underline"
                        style={{ color: CRM_BRAND.primaryDark }}
                      >
                        {t('miniCrm.openInbox')}
                        <RiExternalLinkLine className="size-3" aria-hidden />
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
