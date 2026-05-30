'use client'

import type { MiniCrmLeadFormState } from './constants'
import { useTranslation } from '#i18n'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Tag from '@/app/components/base/tag'
import MemberSelector from '@/app/components/header/account-setting/members-page/transfer-ownership-modal/member-selector'
import { MINI_CRM_PRESET_TAGS, MINI_CRM_STAGES } from './constants'

type CrmLeadEditorProps = {
  formState: MiniCrmLeadFormState
  isSaving: boolean
  onChange: (next: MiniCrmLeadFormState) => void
  onSave: () => void
  onCancel: () => void
  resolveStageLabel: (stage: string) => string
}

export function CrmLeadEditor({
  formState,
  isSaving,
  onChange,
  onSave,
  onCancel,
  resolveStageLabel,
}: CrmLeadEditorProps) {
  const { t } = useTranslation('common')

  const appendPresetTag = (presetTag: string) => {
    const currentTags = formState.tags_input
      .split(/[,;]/)
      .map(tag => tag.trim())
      .filter(Boolean)
    if (currentTags.includes(presetTag))
      return
    onChange({
      ...formState,
      tags_input: [...currentTags, presetTag].join(', '),
    })
  }

  return (
    <div className="flex flex-wrap gap-4">
      <div>
        <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colStage')}</div>
        <select
          className="h-9 min-w-[140px] rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 system-sm-regular text-text-primary"
          value={formState.stage}
          onChange={(e) => {
            onChange({ ...formState, stage: e.target.value })
          }}
        >
          {MINI_CRM_STAGES.map(stageValue => (
            <option key={stageValue} value={stageValue}>
              {resolveStageLabel(stageValue)}
            </option>
          ))}
        </select>
      </div>
      <div className="min-w-[200px] flex-1">
        <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colOwner')}</div>
        <MemberSelector
          value={formState.owner_account_id ?? undefined}
          onSelect={(accountId: string) => {
            onChange({ ...formState, owner_account_id: accountId })
          }}
        />
        {formState.owner_account_id && (
          <button
            type="button"
            className="mt-1 text-xs text-text-accent hover:opacity-80"
            onClick={() => onChange({ ...formState, owner_account_id: null })}
          >
            {t('miniCrm.ownerClear')}
          </button>
        )}
      </div>
      <div className="min-w-[160px] flex-1">
        <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colPhone')}</div>
        <Input
          value={formState.contact_phone}
          onChange={(e) => {
            onChange({ ...formState, contact_phone: e.target.value })
          }}
          placeholder={t('miniCrm.contactPhonePlaceholder')}
        />
      </div>
      <div className="min-w-[180px] flex-[2]">
        <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.colEmail')}</div>
        <Input
          value={formState.contact_email}
          onChange={(e) => {
            onChange({ ...formState, contact_email: e.target.value })
          }}
          placeholder={t('miniCrm.contactEmailPlaceholder')}
        />
      </div>
      <div className="min-w-[200px] flex-1">
        <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.sourceOverrideLabel')}</div>
        <Input
          value={formState.source_override}
          onChange={(e) => {
            onChange({ ...formState, source_override: e.target.value })
          }}
          placeholder={t('miniCrm.sourceOverridePlaceholder')}
        />
      </div>
      <div className="w-full min-w-[240px] flex-[2]">
        <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.tagsLabel')}</div>
        <Input
          value={formState.tags_input}
          onChange={(e) => {
            onChange({ ...formState, tags_input: e.target.value })
          }}
          placeholder={t('miniCrm.tagsPlaceholder')}
        />
        <div className="mt-2 flex flex-wrap gap-1">
          {MINI_CRM_PRESET_TAGS.map((presetTag) => {
            const labelKey = {
              'VIP': 'miniCrm.presetTagVip',
              'New customer': 'miniCrm.presetTagNewCustomer',
              'Ticket': 'miniCrm.presetTagTicket',
              'Zalo care': 'miniCrm.presetTagZaloCare',
            }[presetTag] as 'miniCrm.presetTagVip' | 'miniCrm.presetTagNewCustomer' | 'miniCrm.presetTagTicket' | 'miniCrm.presetTagZaloCare'
            return (
              <button
                key={presetTag}
                type="button"
                className="inline-flex"
                onClick={() => appendPresetTag(presetTag)}
              >
                <Tag color="gray" className="cursor-pointer hover:opacity-80">
                  {t(labelKey)}
                </Tag>
              </button>
            )
          })}
        </div>
      </div>
      <div className="w-full min-w-[240px] flex-[2]">
        <div className="mb-1 text-xs text-text-tertiary">{t('miniCrm.notesLabel')}</div>
        <textarea
          className="min-h-[72px] w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 py-1.5 system-sm-regular text-text-primary"
          value={formState.notes}
          onChange={(e) => {
            onChange({ ...formState, notes: e.target.value })
          }}
          placeholder={t('miniCrm.notesPlaceholder')}
        />
      </div>
      <div className="flex items-end gap-2">
        <Button
          variant="primary"
          loading={isSaving}
          onClick={(e) => {
            e.stopPropagation()
            onSave()
          }}
        >
          {t('miniCrm.save')}
        </Button>
        <Button
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation()
            onCancel()
          }}
        >
          {t('operation.cancel')}
        </Button>
      </div>
    </div>
  )
}
