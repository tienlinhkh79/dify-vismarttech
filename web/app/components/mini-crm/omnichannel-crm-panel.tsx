'use client'

import type { MiniCrmLeadRow } from '@/service/tools'
import { useTranslation } from '#i18n'
import { useCallback, useEffect, useState } from 'react'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Loading from '@/app/components/base/loading'
import { toast } from '@/app/components/base/ui/toast'
import MemberSelector from '@/app/components/header/account-setting/members-page/transfer-ownership-modal/member-selector'
import Link from '@/next/link'
import { getMiniCrmLead, patchMiniCrmLead } from '@/service/tools'
import { MINI_CRM_STAGES, tagsArrayToInput, tagsInputToArray } from './constants'
import { CrmLeadTags } from './crm-lead-tags'
import { CrmLeadTimeline } from './crm-lead-timeline'
import { StageTag } from './stage-tag'

type OmnichannelCrmPanelProps = {
  conversationId: string
  channelId: string
  onLeadSaved?: (lead: MiniCrmLeadRow) => void
}

export function OmnichannelCrmPanel({ conversationId, channelId, onLeadSaved }: OmnichannelCrmPanelProps) {
  const { t } = useTranslation('common')
  const [leadRow, setLeadRow] = useState<MiniCrmLeadRow | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [stage, setStage] = useState('new')
  const [notes, setNotes] = useState('')
  const [sourceOverride, setSourceOverride] = useState('')
  const [ownerAccountId, setOwnerAccountId] = useState<string | null>(null)
  const [tagsInput, setTagsInput] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [contactEmail, setContactEmail] = useState('')

  const resolveStageLabel = useCallback((stageValue: string) => {
    const labels: Record<string, string> = {
      new: t('miniCrm.stageNew'),
      qualified: t('miniCrm.stageQualified'),
      won: t('miniCrm.stageWon'),
      lost: t('miniCrm.stageLost'),
    }
    return labels[stageValue] || stageValue
  }, [t])

  const loadLead = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await getMiniCrmLead(conversationId)
      const row = response.data
      setLeadRow(row)
      setStage(row.stage)
      setNotes(row.notes || '')
      setSourceOverride(row.source_override || '')
      setOwnerAccountId(row.owner_account_id ?? null)
      setTagsInput(tagsArrayToInput(row.tags))
      setContactPhone(row.contact_phone || '')
      setContactEmail(row.contact_email || '')
    }
    catch {
      toast.error(t('miniCrm.errorLoad'))
    }
    finally {
      setIsLoading(false)
    }
  }, [conversationId, t])

  useEffect(() => {
    void loadLead()
  }, [loadLead])

  const saveLead = async () => {
    setIsSaving(true)
    try {
      const response = await patchMiniCrmLead(conversationId, {
        stage,
        notes,
        source_override: sourceOverride || null,
        owner_account_id: ownerAccountId,
        tags: tagsInputToArray(tagsInput),
        contact_phone: contactPhone || null,
        contact_email: contactEmail || null,
      })
      setLeadRow(response.data)
      onLeadSaved?.(response.data)
      toast.success(t('miniCrm.saveSuccess'))
    }
    catch {
      toast.error(t('miniCrm.errorSave'))
    }
    finally {
      setIsSaving(false)
    }
  }

  if (isLoading && !leadRow) {
    return (
      <div className="flex min-h-[8rem] items-center justify-center">
        <Loading type="area" />
      </div>
    )
  }

  return (
    <section className="border-t border-divider-subtle pt-6">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold tracking-wide text-text-quaternary uppercase">{t('miniCrm.panelTitle')}</h2>
        <Link
          href={`/mini-crm?conversation_id=${encodeURIComponent(conversationId)}&channel_id=${encodeURIComponent(channelId)}`}
          className="text-xs font-medium text-text-accent-secondary hover:opacity-80"
        >
          {t('miniCrm.openFullCrm')}
        </Link>
      </div>
      <div className="space-y-3 rounded-lg bg-background-default px-3 py-3 ring-1 ring-divider-subtle">
        <CrmLeadTags tags={leadRow?.tags} />
        <div>
          <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colStage')}</div>
          <div className="flex items-center gap-2">
            <select
              className="h-9 min-w-0 flex-1 rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 system-sm-regular text-text-primary"
              value={stage}
              onChange={e => setStage(e.target.value)}
            >
              {MINI_CRM_STAGES.map(stageValue => (
                <option key={stageValue} value={stageValue}>
                  {resolveStageLabel(stageValue)}
                </option>
              ))}
            </select>
            <StageTag stage={stage} />
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colOwner')}</div>
          <MemberSelector
            value={ownerAccountId ?? undefined}
            onSelect={(accountId: string) => setOwnerAccountId(accountId)}
          />
          {ownerAccountId && (
            <button
              type="button"
              className="mt-1 text-xs text-text-accent hover:opacity-80"
              onClick={() => setOwnerAccountId(null)}
            >
              {t('miniCrm.ownerClear')}
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 gap-2">
          <div>
            <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colPhone')}</div>
            <Input value={contactPhone} onChange={e => setContactPhone(e.target.value)} placeholder={t('miniCrm.contactPhonePlaceholder')} />
          </div>
          <div>
            <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colEmail')}</div>
            <Input value={contactEmail} onChange={e => setContactEmail(e.target.value)} placeholder={t('miniCrm.contactEmailPlaceholder')} />
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.tagsLabel')}</div>
          <Input value={tagsInput} onChange={e => setTagsInput(e.target.value)} placeholder={t('miniCrm.tagsPlaceholder')} />
        </div>
        <div>
          <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.sourceOverrideLabel')}</div>
          <Input
            value={sourceOverride}
            onChange={e => setSourceOverride(e.target.value)}
            placeholder={t('miniCrm.sourceOverridePlaceholder')}
          />
        </div>
        <div>
          <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.notesLabel')}</div>
          <textarea
            className="min-h-[72px] w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 py-1.5 system-sm-regular text-text-primary"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder={t('miniCrm.notesPlaceholder')}
          />
        </div>
        <Button className="w-full" variant="primary" size="small" loading={isSaving} onClick={() => void saveLead()}>
          {t('miniCrm.save')}
        </Button>
        <div className="border-t border-divider-subtle pt-3">
          <div className="mb-2 text-xs font-medium text-text-tertiary">{t('miniCrm.activityLogTitle')}</div>
          <CrmLeadTimeline conversationId={conversationId} />
        </div>
      </div>
    </section>
  )
}
