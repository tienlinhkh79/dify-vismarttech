'use client'

import type { OmnichannelCannedResponse, OmnichannelMessage } from '@/service/tools'
import type { FC, ReactNode } from 'react'
import { RiAttachmentLine, RiBold, RiItalic, RiMagicLine, RiSendPlane2Fill, RiStrikethrough, RiTimeLine } from '@remixicon/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from '#i18n'
import ActionButton from '@/app/components/base/action-button'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { toast } from '@/app/components/base/ui/toast'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/app/components/base/ui/dropdown-menu'
import {
  patchOmnichannelConversation,
  sendOmnichannelTyping,
  suggestOmnichannelReply,
} from '@/service/tools'
import { cn } from '@/utils/classnames'
import OmnichannelCannedResponsesModal from './omnichannel-canned-responses-modal'
import OmnichannelComposerEmojiPopover from './omnichannel-composer-emoji-popover'
import {
  applyCannedResponse,
  clearComposerDraft,
  extractSlashQuery,
  filterCannedResponses,
  getChannelMessageMaxLength,
  insertAtCursor,
  isMetaMessagingChannel,
  isMessagingWindowOpen,
  loadComposerDraft,
  loadSendHotkey,
  saveComposerDraft,
  saveSendHotkey,
  snoozeUntilFromPreset,
  supportsComposerFormatting,
  supportsComposerTyping,
  wrapComposerSelection,
  type SendHotkey,
  type TextWrapMark,
} from './omnichannel-composer-utils'

type AttachmentType = 'image' | 'video' | 'audio' | 'file'

export type OmnichannelComposerProps = {
  channelId: string | null
  conversationId: string | null
  channelType: string | undefined
  disabled?: boolean
  isSending?: boolean
  isUploading?: boolean
  lastInboundAt?: string
  text: string
  onTextChange: (value: string) => void
  internalNote: boolean
  onInternalNoteChange: (value: boolean) => void
  replyTo: OmnichannelMessage | null
  onReplyToClear: () => void
  attachmentUrl: string
  attachmentType: AttachmentType
  onAttachmentTypeChange: (value: AttachmentType) => void
  attachmentOpen: boolean
  onAttachmentOpenChange: (open: boolean) => void
  attachmentName: string
  attachmentUploadProgress: number | null
  attachmentInputRef: React.RefObject<HTMLInputElement | null>
  onAttachmentFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onAttachmentFile?: (file: File) => void
  onClearAttachment: () => void
  supportsAttachments: boolean
  supportsRichComposer: boolean
  richComposerOpen: boolean
  onRichComposerToggle: () => void
  cannedResponses: OmnichannelCannedResponse[]
  onCannedResponsesChanged: () => void
  canSend: boolean
  onSend: () => void
  onConversationUpdated?: () => void
  richComposerPanel?: ReactNode
}

const OmnichannelComposer: FC<OmnichannelComposerProps> = ({
  channelId,
  conversationId,
  channelType,
  disabled,
  isSending,
  isUploading,
  lastInboundAt,
  text,
  onTextChange,
  internalNote,
  onInternalNoteChange,
  replyTo,
  onReplyToClear,
  attachmentUrl,
  attachmentType,
  onAttachmentTypeChange,
  attachmentOpen,
  onAttachmentOpenChange,
  attachmentName,
  attachmentUploadProgress,
  attachmentInputRef,
  onAttachmentFileChange,
  onAttachmentFile,
  onClearAttachment,
  supportsAttachments,
  supportsRichComposer,
  richComposerOpen,
  onRichComposerToggle,
  cannedResponses,
  onCannedResponsesChanged,
  canSend,
  onSend,
  onConversationUpdated,
  richComposerPanel,
}) => {
  const { t } = useTranslation('common')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const [cursor, setCursor] = useState(0)
  const [selectionEnd, setSelectionEnd] = useState(0)
  const [sendHotkey, setSendHotkey] = useState<SendHotkey>('enter')
  const [cannedModalOpen, setCannedModalOpen] = useState(false)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [isSnoozing, setIsSnoozing] = useState(false)
  const typingOffTimerRef = useRef<number | null>(null)
  const typingSentRef = useRef(false)
  const [slashActive, setSlashActive] = useState(false)
  const [slashQuery, setSlashQuery] = useState('')
  const [slashStart, setSlashStart] = useState(-1)
  const draftLoadedForRef = useRef('')

  const composerMode = internalNote ? 'note' : 'reply'
  const maxLength = getChannelMessageMaxLength(channelType)
  const charsRemaining = maxLength != null ? maxLength - text.length : null
  const isOverLimit = charsRemaining != null && charsRemaining < 0
  const composerDisabled = disabled || isSending || isUploading
  const showMessagingWindowWarning = !internalNote
    && isMetaMessagingChannel(channelType)
    && !!lastInboundAt
    && !isMessagingWindowOpen(lastInboundAt)
  const showFormatting = supportsComposerFormatting(channelType) && !internalNote
  const showTyping = supportsComposerTyping(channelType) && !internalNote

  const slashMatches = useMemo(
    () => (slashActive ? filterCannedResponses(cannedResponses, slashQuery) : []),
    [cannedResponses, slashActive, slashQuery],
  )

  useEffect(() => {
    setSendHotkey(loadSendHotkey())
  }, [])

  useEffect(() => {
    if (!conversationId) {
      onTextChange('')
      return
    }
    const loadKey = `${conversationId}:${composerMode}`
    if (draftLoadedForRef.current === loadKey)
      return
    draftLoadedForRef.current = loadKey
    onTextChange(loadComposerDraft(conversationId, composerMode))
    onReplyToClear()
    onAttachmentOpenChange(false)
    onClearAttachment()
  // eslint-disable-next-line react-hooks/exhaustive-deps -- reset composer when conversation or mode changes
  }, [conversationId, composerMode])

  useEffect(() => {
    if (!conversationId)
      return
    saveComposerDraft(conversationId, composerMode, text)
  }, [conversationId, composerMode, text])

  useEffect(() => {
    if (!showTyping || !channelId || !conversationId || internalNote || composerDisabled) {
      if (typingOffTimerRef.current != null) {
        window.clearTimeout(typingOffTimerRef.current)
        typingOffTimerRef.current = null
      }
      if (typingSentRef.current && channelId && conversationId) {
        void sendOmnichannelTyping(channelId, conversationId, 'typing_off')
        typingSentRef.current = false
      }
      return
    }
    if (!text.trim()) {
      return
    }
    void sendOmnichannelTyping(channelId, conversationId, 'typing_on').then(() => {
      typingSentRef.current = true
    }).catch(() => {})
    if (typingOffTimerRef.current != null)
      window.clearTimeout(typingOffTimerRef.current)
    typingOffTimerRef.current = window.setTimeout(() => {
      void sendOmnichannelTyping(channelId, conversationId, 'typing_off').finally(() => {
        typingSentRef.current = false
      })
    }, 4000)
    return () => {
      if (typingOffTimerRef.current != null) {
        window.clearTimeout(typingOffTimerRef.current)
        typingOffTimerRef.current = null
      }
    }
  }, [channelId, composerDisabled, conversationId, internalNote, showTyping, text])

  const syncSlashState = useCallback((value: string, nextCursor: number) => {
    const slash = extractSlashQuery(value, nextCursor)
    setSlashActive(slash.active)
    setSlashQuery(slash.query)
    setSlashStart(slash.start)
  }, [])

  const onTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    const nextCursor = e.target.selectionStart ?? value.length
    onTextChange(value)
    setCursor(nextCursor)
    syncSlashState(value, nextCursor)
  }

  const onTextareaSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget
    const start = target.selectionStart ?? 0
    const end = target.selectionEnd ?? start
    setCursor(start)
    setSelectionEnd(end)
    syncSlashState(target.value, start)
  }

  const applyFormatting = (mark: TextWrapMark) => {
    const result = wrapComposerSelection(text, cursor, selectionEnd, mark)
    onTextChange(result.nextText)
    requestAnimationFrame(() => {
      const el = textareaRef.current
      if (!el)
        return
      el.focus()
      el.setSelectionRange(result.nextCursor, result.nextSelectionEnd)
      setCursor(result.nextCursor)
      setSelectionEnd(result.nextSelectionEnd)
    })
  }

  const onSuggestReply = async () => {
    if (!channelId || !conversationId || internalNote)
      return
    setIsSuggesting(true)
    try {
      const res = await suggestOmnichannelReply(channelId, conversationId)
      const suggestion = res.data?.text?.trim()
      if (!suggestion) {
        toast.error(t('settings.omnichannelComposerSuggestEmpty'))
        return
      }
      onTextChange(suggestion)
      toast.success(t('settings.omnichannelComposerSuggestSuccess'))
    }
    catch (err) {
      const message = err instanceof Response
        ? await err.json().then((body: { message?: string }) => body.message).catch(() => '')
        : ''
      toast.error(message || t('settings.omnichannelComposerSuggestError'))
    }
    finally {
      setIsSuggesting(false)
    }
  }

  const onSnooze = async (preset: '1h' | 'tomorrow' | '3d') => {
    if (!channelId || !conversationId)
      return
    setIsSnoozing(true)
    try {
      await patchOmnichannelConversation(channelId, conversationId, {
        status: 'snoozed',
        snoozed_until: snoozeUntilFromPreset(preset),
      })
      toast.success(t('settings.omnichannelComposerSnoozeSuccess'))
      onConversationUpdated?.()
    }
    catch {
      toast.error(t('settings.omnichannelComposerSnoozeError'))
    }
    finally {
      setIsSnoozing(false)
    }
  }

  const applyCanned = (content: string) => {
    if (slashStart >= 0) {
      const result = applyCannedResponse(text, slashStart, cursor, content)
      onTextChange(result.nextText)
      setSlashActive(false)
      setSlashQuery('')
      setSlashStart(-1)
      requestAnimationFrame(() => {
        const el = textareaRef.current
        if (!el)
          return
        el.focus()
        el.setSelectionRange(result.nextCursor, result.nextCursor)
      })
      return
    }
    onTextChange(content)
  }

  const onEmojiSelect = (emoji: string) => {
    const result = insertAtCursor(text, cursor, emoji)
    onTextChange(result.nextText)
    requestAnimationFrame(() => {
      const el = textareaRef.current
      if (!el)
        return
      el.focus()
      el.setSelectionRange(result.nextCursor, result.nextCursor)
      setCursor(result.nextCursor)
    })
  }

  const toggleSendHotkey = () => {
    const next: SendHotkey = sendHotkey === 'enter' ? 'cmd_enter' : 'enter'
    setSendHotkey(next)
    saveSendHotkey(next)
  }

  const shouldSendOnKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashActive && slashMatches.length > 0)
      return false
    if (sendHotkey === 'cmd_enter')
      return e.key === 'Enter' && (e.metaKey || e.ctrlKey)
    return e.key === 'Enter' && !e.shiftKey
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashActive && slashMatches.length > 0 && e.key === 'Tab') {
      e.preventDefault()
      applyCanned(slashMatches[0].content)
      return
    }
    if (!shouldSendOnKeyDown(e) || e.nativeEvent.isComposing)
      return
    e.preventDefault()
    if (composerDisabled || !canSend || isOverLimit)
      return
    onSend()
  }

  const ingestAttachmentFile = (file: File) => {
    if (onAttachmentFile) {
      onAttachmentFile(file)
      return
    }
    if (!attachmentInputRef.current)
      return
    const dt = new DataTransfer()
    dt.items.add(file)
    attachmentInputRef.current.files = dt.files
    attachmentInputRef.current.dispatchEvent(new Event('change', { bubbles: true }))
  }

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (!supportsAttachments || internalNote)
      return
    const file = e.clipboardData.files?.[0]
    if (!file)
      return
    e.preventDefault()
    ingestAttachmentFile(file)
  }

  const onDrop = (e: React.DragEvent<HTMLTextAreaElement>) => {
    if (!supportsAttachments || internalNote)
      return
    const file = e.dataTransfer.files?.[0]
    if (!file)
      return
    e.preventDefault()
    ingestAttachmentFile(file)
  }

  const onSendClick = () => {
    if (!conversationId || composerDisabled || !canSend || isOverLimit)
      return
    if (conversationId)
      clearComposerDraft(conversationId, composerMode)
    onSend()
  }

  return (
    <div className="shrink-0 border-t border-divider-subtle bg-background-default px-4 py-3 md:px-6">
      {showMessagingWindowWarning && (
        <div className="mb-2 rounded-lg border border-[rgba(245,158,11,0.35)] bg-[rgba(245,158,11,0.08)] px-3 py-2 text-xs text-text-secondary">
          {t('settings.omnichannelComposerMessagingWindowClosed')}
        </div>
      )}
      {replyTo && !internalNote && (
        <div className="mb-2 flex items-start justify-between gap-2 rounded-lg bg-state-base-hover px-3 py-2 text-xs text-text-secondary ring-1 ring-divider-subtle">
          <div className="min-w-0">
            <div className="font-medium text-text-primary">{t('settings.omnichannelReplyingTo')}</div>
            <div className="line-clamp-2">{replyTo.content}</div>
          </div>
          <button type="button" className="shrink-0 text-text-accent hover:opacity-80" onClick={onReplyToClear}>
            {t('operation.cancel', { ns: 'common' })}
          </button>
        </div>
      )}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <div className="inline-flex rounded-lg bg-state-base-hover p-0.5">
          <button
            type="button"
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium',
              !internalNote ? 'bg-background-default text-text-primary shadow-sm' : 'text-text-tertiary',
            )}
            onClick={() => onInternalNoteChange(false)}
          >
            {t('settings.omnichannelComposerModeReply')}
          </button>
          <button
            type="button"
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium',
              internalNote ? 'bg-background-default text-text-primary shadow-sm' : 'text-text-tertiary',
            )}
            onClick={() => onInternalNoteChange(true)}
          >
            {t('settings.omnichannelComposerModeNote')}
          </button>
        </div>
        {supportsRichComposer && !internalNote && (
          <button
            type="button"
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium',
              richComposerOpen ? 'bg-state-base-hover text-text-primary' : 'text-text-tertiary hover:text-text-secondary',
            )}
            onClick={onRichComposerToggle}
          >
            {t('settings.omnichannelRichComposerToggle')}
          </button>
        )}
        <button
          type="button"
          className="rounded-md px-2.5 py-1 text-xs font-medium text-text-tertiary hover:text-text-secondary"
          onClick={() => setCannedModalOpen(true)}
        >
          {t('settings.omnichannelCannedManage')}
        </button>
        {!internalNote && (
          <Button
            type="button"
            size="small"
            variant="secondary"
            loading={isSuggesting}
            disabled={composerDisabled || !channelId || !conversationId}
            onClick={() => void onSuggestReply()}
          >
            <RiMagicLine className="mr-1 inline h-3.5 w-3.5" />
            {t('settings.omnichannelComposerSuggestReply')}
          </Button>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="rounded-md px-2.5 py-1 text-xs font-medium text-text-tertiary hover:text-text-secondary disabled:opacity-40"
            disabled={!channelId || !conversationId || isSnoozing}
          >
            <RiTimeLine className="mr-1 inline h-3.5 w-3.5" />
            {t('settings.omnichannelComposerSnooze')}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={() => void onSnooze('1h')}>
              {t('settings.omnichannelComposerSnooze1h')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => void onSnooze('tomorrow')}>
              {t('settings.omnichannelComposerSnoozeTomorrow')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => void onSnooze('3d')}>
              {t('settings.omnichannelComposerSnooze3d')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        {!!cannedResponses.length && (
          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-md px-2.5 py-1 text-xs font-medium text-text-tertiary hover:text-text-secondary">
              {t('settings.omnichannelCannedResponses')}
            </DropdownMenuTrigger>
            <DropdownMenuContent className="max-h-64 w-72 overflow-y-auto">
              {cannedResponses.map(item => (
                <DropdownMenuItem
                  key={item.id}
                  className="h-auto cursor-pointer flex-col items-start gap-0.5 py-2"
                  onClick={() => applyCanned(item.content)}
                >
                  <span className="system-sm-medium text-text-primary">{item.title}</span>
                  {item.shortcut && (
                    <span className="text-[11px] text-text-quaternary">
                      /
                      {item.shortcut}
                    </span>
                  )}
                  <span className="line-clamp-2 text-xs text-text-tertiary">{item.content}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
        <button
          type="button"
          className="ml-auto rounded-md px-2 py-1 text-[11px] text-text-quaternary hover:text-text-secondary"
          onClick={toggleSendHotkey}
          title={t('settings.omnichannelComposerSendHotkeyHint')}
        >
          {sendHotkey === 'enter'
            ? t('settings.omnichannelComposerSendHotkeyEnter')
            : t('settings.omnichannelComposerSendHotkeyCmdEnter')}
        </button>
        {maxLength != null && (
          <span className={cn('text-[11px] tabular-nums', isOverLimit ? 'text-text-destructive' : 'text-text-quaternary')}>
            {isOverLimit
              ? t('settings.omnichannelComposerCharsOver', { count: Math.abs(charsRemaining!) })
              : t('settings.omnichannelComposerCharsRemaining', { count: charsRemaining })}
          </span>
        )}
      </div>
      {showFormatting && (
        <div className="mb-2 flex items-center gap-1">
          <ActionButton type="button" size="l" aria-label={t('settings.omnichannelComposerBold')} onClick={() => applyFormatting('bold')}>
            <RiBold className="h-4 w-4" />
          </ActionButton>
          <ActionButton type="button" size="l" aria-label={t('settings.omnichannelComposerItalic')} onClick={() => applyFormatting('italic')}>
            <RiItalic className="h-4 w-4" />
          </ActionButton>
          <ActionButton type="button" size="l" aria-label={t('settings.omnichannelComposerStrike')} onClick={() => applyFormatting('strike')}>
            <RiStrikethrough className="h-4 w-4" />
          </ActionButton>
        </div>
      )}
      <div
        className={cn(
          'relative flex items-end gap-2 rounded-2xl border border-divider-subtle bg-components-input-bg-normal px-3 py-2 shadow-sm ring-1 ring-divider-subtle ring-inset',
          internalNote && 'border-dashed bg-state-base-hover',
          composerDisabled && 'opacity-60',
        )}
        onDragOver={e => supportsAttachments && !internalNote && e.preventDefault()}
      >
        {slashActive && slashMatches.length > 0 && (
          <div className="absolute bottom-full left-0 z-20 mb-1 max-h-48 w-full overflow-y-auto rounded-xl border border-divider-subtle bg-background-default py-1 shadow-lg">
            {slashMatches.map(item => (
              <button
                key={item.id}
                type="button"
                className="flex w-full flex-col items-start px-3 py-2 text-left hover:bg-state-base-hover"
                onMouseDown={e => e.preventDefault()}
                onClick={() => applyCanned(item.content)}
              >
                <span className="system-sm-medium text-text-primary">{item.title}</span>
                <span className="line-clamp-1 text-xs text-text-tertiary">{item.content}</span>
              </button>
            ))}
          </div>
        )}
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={onTextareaChange}
          onSelect={onTextareaSelect}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
          onDrop={onDrop}
          disabled={composerDisabled || !conversationId}
          className="max-h-[160px] min-h-[36px] flex-1 resize-y bg-transparent py-1.5 system-sm-regular text-text-primary outline-none placeholder:text-text-quaternary disabled:cursor-not-allowed"
          placeholder={
            internalNote
              ? t('settings.omnichannelInternalNotePlaceholder')
              : t('settings.omnichannelComposerPlaceholder')
          }
        />
        <div className="flex shrink-0 items-center gap-1 pb-0.5">
          {!internalNote && (
            <OmnichannelComposerEmojiPopover
              disabled={composerDisabled || !conversationId}
              onSelect={onEmojiSelect}
            />
          )}
          {supportsAttachments && !internalNote && (
            <ActionButton
              type="button"
              size="l"
              disabled={composerDisabled || !conversationId}
              aria-label={t('settings.omnichannelComposerAttach')}
              aria-expanded={attachmentOpen}
              className={cn(
                attachmentOpen && 'action-btn-active',
                attachmentUrl.trim() && !attachmentOpen && 'text-text-accent',
              )}
              onClick={() => onAttachmentOpenChange(!attachmentOpen)}
            >
              <RiAttachmentLine className="h-5 w-5" />
            </ActionButton>
          )}
          <Button
            type="button"
            variant="primary"
            className="h-8 w-8 shrink-0 rounded-lg px-0"
            loading={isSending}
            disabled={composerDisabled || !conversationId || !canSend || isOverLimit}
            aria-label={internalNote ? t('settings.omnichannelInternalNoteToggle') : t('settings.omnichannelSend')}
            onClick={onSendClick}
          >
            <RiSendPlane2Fill className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <p className="mt-1 text-[11px] text-text-quaternary">
        {t('settings.omnichannelComposerSlashHint')}
      </p>
      {richComposerOpen && supportsRichComposer && !internalNote && (
        <div className="mt-2">
          {richComposerPanel}
        </div>
      )}
      {supportsAttachments && attachmentOpen && (
        <div className="mt-2 space-y-3 rounded-xl border border-divider-subtle bg-background-default/80 px-3 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={attachmentInputRef}
              type="file"
              className="sr-only"
              disabled={composerDisabled || !conversationId}
              onChange={onAttachmentFileChange}
            />
            <Button
              type="button"
              size="small"
              variant="secondary"
              loading={isUploading}
              disabled={composerDisabled || !conversationId}
              onClick={() => attachmentInputRef.current?.click()}
            >
              {t('settings.omnichannelComposerUploadFile')}
            </Button>
            {!!attachmentName && (
              <span className="max-w-[min(100%,280px)] truncate text-xs text-text-secondary">
                {attachmentName}
                {attachmentUploadProgress != null && (
                  <span className="ml-1 text-text-quaternary tabular-nums">
                    {attachmentUploadProgress}
                    %
                  </span>
                )}
              </span>
            )}
            {!!attachmentUrl.trim() && (
              <button
                type="button"
                className="text-xs font-medium text-text-accent-secondary hover:opacity-80 disabled:opacity-40"
                disabled={composerDisabled || !conversationId}
                onClick={onClearAttachment}
              >
                {t('settings.omnichannelComposerRemoveAttachment')}
              </button>
            )}
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <div className="min-w-0 flex-1">
              <label className="mb-1 block text-xs font-medium text-text-tertiary">
                {t('settings.omnichannelComposerAttachmentUrlLabel')}
              </label>
              <Input
                value={attachmentUrl}
                readOnly
                disabled={composerDisabled || !conversationId}
                placeholder={isUploading ? t('settings.omnichannelComposerUploading') : 'https://'}
              />
              <p className="mt-1 text-[11px] leading-snug text-text-quaternary">
                {t('settings.omnichannelComposerAttachmentUrlHint')}
              </p>
            </div>
            <div className="w-full shrink-0 sm:w-36">
              <label className="mb-1 block text-xs font-medium text-text-tertiary">
                {t('settings.omnichannelComposerAttachmentTypeLabel')}
              </label>
              <select
                className="h-9 w-full rounded-lg border-0 bg-components-input-bg-normal px-2 system-sm-regular text-text-primary shadow-sm ring-1 ring-divider-subtle ring-inset"
                value={attachmentType}
                onChange={e => onAttachmentTypeChange(e.target.value as AttachmentType)}
                disabled={composerDisabled || !conversationId}
              >
                <option value="image">{t('settings.omnichannelComposerAttachmentTypeImage')}</option>
                <option value="video">{t('settings.omnichannelComposerAttachmentTypeVideo')}</option>
                <option value="audio">{t('settings.omnichannelComposerAttachmentTypeAudio')}</option>
                <option value="file">{t('settings.omnichannelComposerAttachmentTypeFile')}</option>
              </select>
            </div>
          </div>
        </div>
      )}
      <OmnichannelCannedResponsesModal
        isOpen={cannedModalOpen}
        onClose={() => setCannedModalOpen(false)}
        items={cannedResponses}
        onChanged={onCannedResponsesChanged}
      />
    </div>
  )
}

export default OmnichannelComposer
