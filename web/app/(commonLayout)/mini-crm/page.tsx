'use client'

import { RiContactsBookLine } from '@remixicon/react'
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from '#i18n'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Link from '@/next/link'
import {
  listMiniCrmLeads,
  patchMiniCrmLead,
  type MiniCrmLeadRow,
} from '@/service/tools'

const STAGES = ['new', 'qualified', 'won', 'lost'] as const

const CHANNEL_TYPES = [
  '',
  'facebook_messenger',
  'instagram_dm',
  'tiktok_messaging',
  'zalo_oa',
] as const

type LeadInlineEditFormState = {
  stage: string
  notes: string
  source_override: string
}

const MiniCrmPage = () => {
  const { t } = useTranslation('common')
  const [crmLeadRows, setCrmLeadRows] = useState<MiniCrmLeadRow[]>([])
  const [totalLeadCount, setTotalLeadCount] = useState(0)
  const [pageSize] = useState(30)
  const [selectedChannelTypeFilter, setSelectedChannelTypeFilter] = useState('')
  const [selectedPipelineStageFilter, setSelectedPipelineStageFilter] = useState('')
  const [appliedSearchQuery, setAppliedSearchQuery] = useState('')
  const [searchQueryInput, setSearchQueryInput] = useState('')
  const [isLeadListLoading, setIsLeadListLoading] = useState(false)
  const [listErrorMessage, setListErrorMessage] = useState('')
  const [expandedConversationId, setExpandedConversationId] = useState<string | null>(null)
  const [inlineEditFormStateByConversationId, setInlineEditFormStateByConversationId] = useState<
    Record<string, LeadInlineEditFormState>
  >({})
  const [savingConversationId, setSavingConversationId] = useState<string | null>(null)

  const loadLeadPage = useCallback(async (nextPageOffset: number, appendToExistingRows: boolean) => {
    setIsLeadListLoading(true)
    setListErrorMessage('')
    try {
      const listResponse = await listMiniCrmLeads({
        channel_type: selectedChannelTypeFilter || undefined,
        stage: selectedPipelineStageFilter || undefined,
        search_query: appliedSearchQuery || undefined,
        page_offset: nextPageOffset,
        page_size: pageSize,
      })
      const leadPageRows = listResponse.data || []
      setTotalLeadCount(listResponse.total ?? 0)
      if (appendToExistingRows)
        setCrmLeadRows((previousRows: MiniCrmLeadRow[]) => [...previousRows, ...leadPageRows])
      else
        setCrmLeadRows(leadPageRows)
    }
    catch {
      setListErrorMessage(t('miniCrm.errorLoad'))
    }
    finally {
      setIsLeadListLoading(false)
    }
  }, [selectedChannelTypeFilter, selectedPipelineStageFilter, appliedSearchQuery, pageSize, t])

  useEffect(() => {
    void loadLeadPage(0, false)
  }, [loadLeadPage])

  const beginInlineEditForLeadRow = useCallback((leadRow: MiniCrmLeadRow) => {
    setExpandedConversationId(leadRow.conversation_id)
    setInlineEditFormStateByConversationId((previous: Record<string, LeadInlineEditFormState>) => ({
      ...previous,
      [leadRow.conversation_id]: {
        stage: leadRow.stage,
        notes: leadRow.notes || '',
        source_override: leadRow.source_override || '',
      },
    }))
  }, [])

  const persistInlineLeadEdits = useCallback(async (conversationId: string) => {
    const pendingFormState = inlineEditFormStateByConversationId[conversationId]
    if (!pendingFormState)
      return
    setSavingConversationId(conversationId)
    setListErrorMessage('')
    try {
      const patchResponse = await patchMiniCrmLead(conversationId, {
        stage: pendingFormState.stage,
        notes: pendingFormState.notes,
        source_override: pendingFormState.source_override || null,
      })
      const patchedLeadRow = patchResponse.data
      setCrmLeadRows((previousRows: MiniCrmLeadRow[]) =>
        previousRows.map((leadRow: MiniCrmLeadRow) =>
          leadRow.conversation_id === conversationId ? { ...leadRow, ...patchedLeadRow } : leadRow,
        ),
      )
      setExpandedConversationId(null)
    }
    catch {
      setListErrorMessage(t('miniCrm.errorSave'))
    }
    finally {
      setSavingConversationId(null)
    }
  }, [inlineEditFormStateByConversationId, t])

  const resolvePipelineStageLabel = useMemo(() => {
    const labelByStageValue: Record<string, string> = {
      new: t('miniCrm.stageNew'),
      qualified: t('miniCrm.stageQualified'),
      won: t('miniCrm.stageWon'),
      lost: t('miniCrm.stageLost'),
    }
    return (stageValue: string) => labelByStageValue[stageValue] || stageValue
  }, [t])

  const resolveOmnichannelTypeTitle = useMemo(() => {
    const labelByChannelType: Record<string, string> = {
      facebook_messenger: t('miniCrm.channelType.facebook_messenger'),
      instagram_dm: t('miniCrm.channelType.instagram_dm'),
      tiktok_messaging: t('miniCrm.channelType.tiktok_messaging'),
      zalo_oa: t('miniCrm.channelType.zalo_oa'),
    }
    return (channelTypeValue: string) => labelByChannelType[channelTypeValue] || channelTypeValue
  }, [t])

  const hasMoreLeadPages = crmLeadRows.length < totalLeadCount

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body px-4 py-6 sm:px-8'>
      <div className='mx-auto w-full max-w-6xl'>
        <div className='mb-6 rounded-2xl border border-components-panel-border bg-gradient-to-r from-background-gradient-bg-fill-chat-bg-2 to-background-gradient-bg-fill-chat-bg-1 p-5'>
          <div className='flex flex-col justify-between gap-4 sm:flex-row sm:items-center'>
            <div>
              <h1 className='text-xl font-semibold text-text-primary'>{t('miniCrm.pageTitle')}</h1>
              <p className='mt-1 max-w-2xl text-sm text-text-secondary'>{t('miniCrm.pageSubtitle')}</p>
            </div>
            <div className='hidden shrink-0 items-center gap-3 rounded-xl border border-divider-regular bg-background-default/80 px-3 py-2 backdrop-blur-sm sm:flex'>
              <RiContactsBookLine className='size-9 text-text-accent' aria-hidden />
              <div>
                <div className='text-xs text-text-tertiary'>{t('miniCrm.heroBadgeLabel')}</div>
                <div className='text-sm font-medium text-text-primary'>{t('miniCrm.heroBadgeValue')}</div>
              </div>
            </div>
          </div>
        </div>

        <div className='mb-4 flex flex-wrap items-end gap-3'>
          <div>
            <div className='mb-1 text-xs font-medium text-text-tertiary'>{t('miniCrm.channel')}</div>
            <select
              className='system-sm-regular h-9 min-w-[160px] rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 text-text-primary'
              value={selectedChannelTypeFilter}
              onChange={(e) => {
                setSelectedChannelTypeFilter(e.target.value)
              }}
            >
              <option value="">{t('miniCrm.channelAll')}</option>
              {CHANNEL_TYPES.filter(Boolean).map(ct => (
                <option key={ct} value={ct}>{resolveOmnichannelTypeTitle(ct)}</option>
              ))}
            </select>
          </div>
          <div>
            <div className='mb-1 text-xs font-medium text-text-tertiary'>{t('miniCrm.colStage')}</div>
            <select
              className='system-sm-regular h-9 min-w-[140px] rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 text-text-primary'
              value={selectedPipelineStageFilter}
              onChange={(e) => {
                setSelectedPipelineStageFilter(e.target.value)
              }}
            >
              <option value="">{t('miniCrm.stageAll')}</option>
              {STAGES.map(s => (
                <option key={s} value={s}>{resolvePipelineStageLabel(s)}</option>
              ))}
            </select>
          </div>
          <div className='flex min-w-[200px] flex-1 flex-col'>
            <div className='mb-1 text-xs font-medium text-text-tertiary'>{t('miniCrm.filterSearchPlaceholder')}</div>
            <div className='flex gap-2'>
              <Input
                value={searchQueryInput}
                onChange={e => setSearchQueryInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setAppliedSearchQuery(searchQueryInput.trim())
                  }
                }}
                placeholder={t('miniCrm.filterSearchPlaceholder')}
              />
              <Button
                variant='primary'
                className='shrink-0'
                onClick={() => setAppliedSearchQuery(searchQueryInput.trim())}
              >
                {t('operation.search')}
              </Button>
            </div>
          </div>
        </div>

        {listErrorMessage && <div className='mb-3 text-sm text-text-destructive'>{listErrorMessage}</div>}
        <div className='mb-2 text-xs text-text-tertiary'>{t('miniCrm.total', { count: totalLeadCount })}</div>

        <div className='overflow-x-auto rounded-xl border border-divider-regular bg-background-default shadow-sm'>
          <table className='w-full min-w-[720px] border-collapse text-left text-sm'>
            <thead>
              <tr className='border-b border-divider-regular bg-background-section-burn'>
                <th className='px-3 py-2 font-medium text-text-secondary'>{t('miniCrm.colContact')}</th>
                <th className='px-3 py-2 font-medium text-text-secondary'>{t('miniCrm.channel')}</th>
                <th className='px-3 py-2 font-medium text-text-secondary'>{t('miniCrm.colSource')}</th>
                <th className='px-3 py-2 font-medium text-text-secondary'>{t('miniCrm.colStage')}</th>
                <th className='px-3 py-2 font-medium text-text-secondary'>{t('miniCrm.colLastMessage')}</th>
                <th className='px-3 py-2 font-medium text-text-secondary' />
              </tr>
            </thead>
            <tbody>
              {isLeadListLoading && !crmLeadRows.length
                ? (
                    <tr>
                      <td colSpan={6} className='px-3 py-8 text-center text-text-tertiary'>…</td>
                    </tr>
                  )
                : crmLeadRows.map(leadRow => (
                    <Fragment key={leadRow.conversation_id}>
                      <tr
                        className='cursor-pointer border-b border-divider-subtle hover:bg-state-base-hover'
                        onClick={() => beginInlineEditForLeadRow(leadRow)}
                      >
                        <td className='px-3 py-2 text-text-primary'>
                          <div className='font-medium'>
                            {(leadRow.participant_display_name || '').trim() || leadRow.external_user_id}
                          </div>
                          <div className='text-xs text-text-tertiary'>{leadRow.external_user_id}</div>
                        </td>
                        <td className='px-3 py-2 text-text-secondary'>
                          {(leadRow.channel_name || '').trim() || resolveOmnichannelTypeTitle(leadRow.channel_type)}
                        </td>
                        <td className='px-3 py-2 text-text-secondary'>{leadRow.source_display}</td>
                        <td className='px-3 py-2 text-text-secondary'>{resolvePipelineStageLabel(leadRow.stage)}</td>
                        <td className='px-3 py-2 text-text-tertiary'>
                          {leadRow.last_message_at ? new Date(leadRow.last_message_at).toLocaleString() : '-'}
                        </td>
                        <td className='px-3 py-2'>
                          <Link
                            href={`/omnichannel?channel_id=${encodeURIComponent(leadRow.channel_id)}&conversation_id=${encodeURIComponent(leadRow.conversation_id)}`}
                            className='text-xs font-medium text-text-accent'
                            onClick={e => e.stopPropagation()}
                          >
                            {t('miniCrm.openInbox')}
                          </Link>
                        </td>
                      </tr>
                      {expandedConversationId === leadRow.conversation_id
                        && inlineEditFormStateByConversationId[leadRow.conversation_id] && (
                        <tr className='border-b border-divider-subtle bg-background-section-burn'>
                          <td colSpan={6} className='px-3 py-3'>
                            <div className='flex flex-wrap gap-4'>
                              <div>
                                <div className='mb-1 text-xs text-text-tertiary'>{t('miniCrm.colStage')}</div>
                                <select
                                  className='system-sm-regular h-9 rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2'
                                  value={inlineEditFormStateByConversationId[leadRow.conversation_id].stage}
                                  onChange={(e) => {
                                    const nextStage = e.target.value
                                    setInlineEditFormStateByConversationId((
                                      previous: Record<string, LeadInlineEditFormState>,
                                    ) => ({
                                      ...previous,
                                      [leadRow.conversation_id]: {
                                        ...previous[leadRow.conversation_id]!,
                                        stage: nextStage,
                                      },
                                    }))
                                  }}
                                >
                                  {STAGES.map(stageValue => (
                                    <option key={stageValue} value={stageValue}>
                                      {resolvePipelineStageLabel(stageValue)}
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <div className='min-w-[200px] flex-1'>
                                <div className='mb-1 text-xs text-text-tertiary'>{t('miniCrm.sourceOverrideLabel')}</div>
                                <Input
                                  value={inlineEditFormStateByConversationId[leadRow.conversation_id].source_override}
                                  onChange={(e) => {
                                    const nextSourceOverride = e.target.value
                                    setInlineEditFormStateByConversationId((
                                      previous: Record<string, LeadInlineEditFormState>,
                                    ) => ({
                                      ...previous,
                                      [leadRow.conversation_id]: {
                                        ...previous[leadRow.conversation_id]!,
                                        source_override: nextSourceOverride,
                                      },
                                    }))
                                  }}
                                  placeholder={t('miniCrm.sourceOverridePlaceholder')}
                                />
                              </div>
                              <div className='w-full min-w-[240px] flex-[2]'>
                                <div className='mb-1 text-xs text-text-tertiary'>{t('miniCrm.notesLabel')}</div>
                                <textarea
                                  className='system-sm-regular min-h-[72px] w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 py-1.5 text-text-primary'
                                  value={inlineEditFormStateByConversationId[leadRow.conversation_id].notes}
                                  onChange={(e) => {
                                    const nextNotes = e.target.value
                                    setInlineEditFormStateByConversationId((
                                      previous: Record<string, LeadInlineEditFormState>,
                                    ) => ({
                                      ...previous,
                                      [leadRow.conversation_id]: {
                                        ...previous[leadRow.conversation_id]!,
                                        notes: nextNotes,
                                      },
                                    }))
                                  }}
                                  placeholder={t('miniCrm.notesPlaceholder')}
                                />
                              </div>
                              <div className='flex items-end gap-2'>
                                <Button
                                  variant='primary'
                                  loading={savingConversationId === leadRow.conversation_id}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    void persistInlineLeadEdits(leadRow.conversation_id)
                                  }}
                                >
                                  {t('miniCrm.save')}
                                </Button>
                                <Button
                                  variant='secondary'
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setExpandedConversationId(null)
                                  }}
                                >
                                  {t('operation.cancel')}
                                </Button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
            </tbody>
          </table>
        </div>

        {hasMoreLeadPages && (
          <div className='mt-4 flex justify-center'>
            <Button
              variant='secondary'
              loading={isLeadListLoading}
              onClick={() => void loadLeadPage(crmLeadRows.length, true)}
            >
              {t('miniCrm.loadMore')}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default MiniCrmPage
