'use client'

import type { OmnichannelCannedResponse } from '@/service/tools'
import type { FC } from 'react'
import { useTranslation } from '#i18n'
import { useState } from 'react'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { toast } from '@/app/components/base/ui/toast'
import { createOmnichannelCannedResponse, deleteOmnichannelCannedResponse } from '@/service/tools'

type OmnichannelCannedResponsesModalProps = {
  isOpen: boolean
  onClose: () => void
  items: OmnichannelCannedResponse[]
  onChanged: () => void
}

const OmnichannelCannedResponsesModal: FC<OmnichannelCannedResponsesModalProps> = ({
  isOpen,
  onClose,
  items,
  onChanged,
}) => {
  const { t } = useTranslation('common')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [shortcut, setShortcut] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const onCreate = async () => {
    if (!title.trim() || !content.trim()) {
      toast.error(t('settings.omnichannelCannedValidation'))
      return
    }
    setIsSaving(true)
    try {
      await createOmnichannelCannedResponse({
        title: title.trim(),
        content: content.trim(),
        shortcut: shortcut.trim() || undefined,
      })
      setTitle('')
      setContent('')
      setShortcut('')
      onChanged()
      toast.success(t('settings.omnichannelCannedCreateSuccess'))
    }
    catch {
      toast.error(t('settings.omnichannelCannedCreateError'))
    }
    finally {
      setIsSaving(false)
    }
  }

  const onDelete = async (id: string) => {
    try {
      await deleteOmnichannelCannedResponse(id)
      onChanged()
      toast.success(t('settings.omnichannelCannedDeleteSuccess'))
    }
    catch {
      toast.error(t('settings.omnichannelCannedDeleteError'))
    }
  }

  return (
    <Modal isShow={isOpen} onClose={onClose} title={t('settings.omnichannelCannedManageTitle')}>
      <div className="space-y-4">
        <div className="space-y-2 rounded-xl border border-divider-subtle p-3">
          <div className="text-xs font-medium text-text-secondary">{t('settings.omnichannelCannedCreateTitle')}</div>
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder={t('settings.omnichannelCannedTitlePlaceholder')} />
          <Input value={shortcut} onChange={e => setShortcut(e.target.value)} placeholder={t('settings.omnichannelCannedShortcutPlaceholder')} />
          <textarea
            rows={3}
            value={content}
            onChange={e => setContent(e.target.value)}
            className="w-full resize-none rounded-lg border-0 bg-components-input-bg-normal px-3 py-2 system-sm-regular text-text-primary shadow-sm ring-1 ring-divider-subtle ring-inset outline-none"
            placeholder={t('settings.omnichannelCannedContentPlaceholder')}
          />
          <Button variant="primary" loading={isSaving} onClick={() => void onCreate()}>
            {t('settings.omnichannelCannedCreateButton')}
          </Button>
        </div>
        <div className="max-h-64 space-y-2 overflow-y-auto">
          {items.length === 0 && (
            <p className="text-xs text-text-tertiary">{t('settings.omnichannelCannedEmpty')}</p>
          )}
          {items.map(item => (
            <div key={item.id} className="flex items-start justify-between gap-2 rounded-lg bg-state-base-hover px-3 py-2">
              <div className="min-w-0">
                <div className="system-sm-medium text-text-primary">{item.title}</div>
                {item.shortcut && (
                  <div className="text-[11px] text-text-quaternary">
                    /
                    {item.shortcut}
                  </div>
                )}
                <div className="line-clamp-2 text-xs text-text-tertiary">{item.content}</div>
              </div>
              <button
                type="button"
                className="shrink-0 text-xs text-text-destructive hover:opacity-80"
                onClick={() => void onDelete(item.id)}
              >
                {t('operation.delete', { ns: 'common' })}
              </button>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  )
}

export default OmnichannelCannedResponsesModal
