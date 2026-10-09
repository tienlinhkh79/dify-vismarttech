'use client'

import type { OmnichannelRichReplyCard, OmnichannelRichReplyPayload } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiAddLine, RiDeleteBinLine } from '@remixicon/react'
import { useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { cn } from '@/utils/classnames'

type ButtonDraft = {
  id: string
  title: string
  action: 'postback' | 'url'
  value: string
}

type OmnichannelRichComposerPanelProps = {
  channelType?: string
  disabled?: boolean
  onSend: (payload: OmnichannelRichReplyPayload) => void | Promise<void>
}

const RICH_CHANNEL_TYPES = new Set([
  'facebook_messenger',
  'instagram_dm',
  'zalo_oa',
  'zalo_personal',
  'tiktok_messaging',
])

const MAX_BUTTONS = 4

function newButtonId() {
  return `btn-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function emptyButton(): ButtonDraft {
  return { id: newButtonId(), title: '', action: 'postback', value: '' }
}

export function OmnichannelRichComposerPanel({
  channelType,
  disabled,
  onSend,
}: OmnichannelRichComposerPanelProps) {
  const { t } = useTranslation('common')
  const [mode, setMode] = useState<'actions' | 'cards'>('actions')
  const [introText, setIntroText] = useState('')
  const [buttons, setButtons] = useState<ButtonDraft[]>([emptyButton(), emptyButton()])
  const [cardTitle, setCardTitle] = useState('')
  const [cardSubtitle, setCardSubtitle] = useState('')
  const [cardImageUrl, setCardImageUrl] = useState('')
  const [cardButtonTitle, setCardButtonTitle] = useState('')
  const [cardButtonUrl, setCardButtonUrl] = useState('')

  const supported = !channelType || RICH_CHANNEL_TYPES.has(channelType)

  const canSendActions = useMemo(() => {
    const intro = introText.trim()
    const validButtons = buttons.filter(b => b.title.trim() && b.value.trim())
    return !!intro && validButtons.length > 0
  }, [buttons, introText])

  const canSendCard = useMemo(() => {
    return !!cardTitle.trim()
  }, [cardTitle])

  const buildActionsPayload = (): OmnichannelRichReplyPayload | null => {
    const intro = introText.trim()
    const validButtons = buttons.filter(b => b.title.trim() && b.value.trim())
    if (!intro || !validButtons.length)
      return null
    return {
      type: 'actions',
      text: intro,
      buttons: validButtons.map((button) => {
        if (button.action === 'url') {
          return { title: button.title.trim(), action: 'url', url: button.value.trim() }
        }
        return { title: button.title.trim(), action: 'postback', payload: button.value.trim() }
      }),
    }
  }

  const buildCardPayload = (): OmnichannelRichReplyPayload | null => {
    const title = cardTitle.trim()
    if (!title)
      return null
    const card: OmnichannelRichReplyCard = { title }
    const subtitle = cardSubtitle.trim()
    if (subtitle)
      card.subtitle = subtitle
    const imageUrl = cardImageUrl.trim()
    if (imageUrl)
      card.image_url = imageUrl
    const btnTitle = cardButtonTitle.trim()
    const btnUrl = cardButtonUrl.trim()
    if (btnTitle && btnUrl) {
      card.buttons = [{ title: btnTitle, action: 'url', url: btnUrl }]
    }
    const intro = introText.trim()
    return {
      type: 'cards',
      ...(intro ? { text: intro } : {}),
      cards: [card],
    }
  }

  const handleSend = async () => {
    const payload = mode === 'actions' ? buildActionsPayload() : buildCardPayload()
    if (!payload)
      return
    await onSend(payload)
    if (mode === 'actions') {
      setIntroText('')
      setButtons([emptyButton(), emptyButton()])
    }
    else {
      setIntroText('')
      setCardTitle('')
      setCardSubtitle('')
      setCardImageUrl('')
      setCardButtonTitle('')
      setCardButtonUrl('')
    }
  }

  if (!supported) {
    return (
      <div className="mt-2 rounded-xl border border-dashed border-divider-subtle px-3 py-2 text-xs text-text-tertiary">
        {t('settings.omnichannelRichComposerUnsupported')}
      </div>
    )
  }

  return (
    <div className="mt-2 space-y-3 rounded-xl border border-divider-subtle bg-background-default/80 px-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={disabled}
          className={cn(
            'rounded-md px-2.5 py-1 text-xs font-medium',
            mode === 'actions' ? 'bg-state-base-hover text-text-primary' : 'text-text-tertiary hover:text-text-secondary',
          )}
          onClick={() => setMode('actions')}
        >
          {t('settings.omnichannelRichComposerModeButtons')}
        </button>
        <button
          type="button"
          disabled={disabled}
          className={cn(
            'rounded-md px-2.5 py-1 text-xs font-medium',
            mode === 'cards' ? 'bg-state-base-hover text-text-primary' : 'text-text-tertiary hover:text-text-secondary',
          )}
          onClick={() => setMode('cards')}
        >
          {t('settings.omnichannelRichComposerModeCard')}
        </button>
        <span className="text-[10px] text-text-quaternary">
          {t('settings.omnichannelRichComposerHint')}
        </span>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          {t('settings.omnichannelRichComposerIntro')}
        </label>
        <Input
          value={introText}
          onChange={e => setIntroText(e.target.value)}
          disabled={disabled}
          placeholder={t('settings.omnichannelRichComposerIntroPlaceholder')}
        />
      </div>

      {mode === 'actions' && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-text-secondary">
            {t('settings.omnichannelRichComposerButtons')}
          </div>
          {buttons.map((button, index) => (
            <div key={button.id} className="grid gap-2 rounded-lg border border-divider-subtle p-2 md:grid-cols-[1fr_120px_1fr_auto]">
              <Input
                value={button.title}
                onChange={(e) => {
                  const next = [...buttons]
                  next[index] = { ...button, title: e.target.value }
                  setButtons(next)
                }}
                disabled={disabled}
                placeholder={t('settings.omnichannelRichComposerButtonTitle')}
              />
              <select
                className="h-9 rounded-lg border border-divider-subtle bg-components-input-bg-normal px-2 text-xs text-text-primary"
                value={button.action}
                disabled={disabled}
                onChange={(e) => {
                  const next = [...buttons]
                  next[index] = { ...button, action: e.target.value as 'postback' | 'url' }
                  setButtons(next)
                }}
              >
                <option value="postback">{t('settings.omnichannelRichComposerActionPostback')}</option>
                <option value="url">{t('settings.omnichannelRichComposerActionUrl')}</option>
              </select>
              <Input
                value={button.value}
                onChange={(e) => {
                  const next = [...buttons]
                  next[index] = { ...button, value: e.target.value }
                  setButtons(next)
                }}
                disabled={disabled}
                placeholder={
                  button.action === 'url'
                    ? t('settings.omnichannelRichComposerButtonUrl')
                    : t('settings.omnichannelRichComposerButtonPayload')
                }
              />
              <button
                type="button"
                className="flex size-9 items-center justify-center rounded-lg text-text-tertiary hover:bg-state-base-hover hover:text-text-destructive"
                disabled={disabled || buttons.length <= 1}
                aria-label={t('operation.delete', { ns: 'common' })}
                onClick={() => setButtons(buttons.filter((_, i) => i !== index))}
              >
                <RiDeleteBinLine className="size-4" />
              </button>
            </div>
          ))}
          <Button
            type="button"
            size="small"
            variant="secondary"
            disabled={disabled || buttons.length >= MAX_BUTTONS}
            onClick={() => setButtons([...buttons, emptyButton()])}
          >
            <RiAddLine className="mr-1 size-3.5" />
            {t('settings.omnichannelRichComposerAddButton')}
          </Button>
        </div>
      )}

      {mode === 'cards' && (
        <div className="grid gap-2 md:grid-cols-2">
          <Input
            value={cardTitle}
            onChange={e => setCardTitle(e.target.value)}
            disabled={disabled}
            placeholder={t('settings.omnichannelRichComposerCardTitle')}
          />
          <Input
            value={cardSubtitle}
            onChange={e => setCardSubtitle(e.target.value)}
            disabled={disabled}
            placeholder={t('settings.omnichannelRichComposerCardSubtitle')}
          />
          <Input
            value={cardImageUrl}
            onChange={e => setCardImageUrl(e.target.value)}
            disabled={disabled}
            placeholder={t('settings.omnichannelRichComposerCardImage')}
            className="md:col-span-2"
          />
          <Input
            value={cardButtonTitle}
            onChange={e => setCardButtonTitle(e.target.value)}
            disabled={disabled}
            placeholder={t('settings.omnichannelRichComposerCardButtonTitle')}
          />
          <Input
            value={cardButtonUrl}
            onChange={e => setCardButtonUrl(e.target.value)}
            disabled={disabled}
            placeholder={t('settings.omnichannelRichComposerCardButtonUrl')}
          />
        </div>
      )}

      <div className="flex justify-end">
        <Button
          type="button"
          variant="primary"
          size="small"
          disabled={disabled || (mode === 'actions' ? !canSendActions : !canSendCard)}
          onClick={() => void handleSend()}
        >
          {t('settings.omnichannelRichComposerSend')}
        </Button>
      </div>
    </div>
  )
}
