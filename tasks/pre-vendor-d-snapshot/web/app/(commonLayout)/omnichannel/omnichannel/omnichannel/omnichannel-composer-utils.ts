export type ComposerMode = 'reply' | 'note'

export type SendHotkey = 'enter' | 'cmd_enter'

const DRAFT_PREFIX = 'dify_omnichannel_draft'
const SEND_HOTKEY_KEY = 'dify_omnichannel_send_hotkey'
const MESSAGING_WINDOW_MS = 24 * 60 * 60 * 1000

const CHANNEL_MESSAGE_MAX_LENGTH: Record<string, number> = {
  facebook_messenger: 2000,
  instagram_dm: 1000,
  zalo_oa: 2000,
  zalo_personal: 2000,
  tiktok_messaging: 6000,
}

const REPLY_TO_CHANNEL_TYPES = new Set([
  'facebook_messenger',
  'instagram_dm',
  'zalo_oa',
  'zalo_personal',
  'tiktok_messaging',
])

const ATTACHMENT_CHANNEL_TYPES = new Set([
  'facebook_messenger',
  'instagram_dm',
  'zalo_oa',
])

const RICH_COMPOSER_CHANNEL_TYPES = new Set([
  'facebook_messenger',
  'instagram_dm',
  'zalo_oa',
  'zalo_personal',
  'tiktok_messaging',
])

const META_MESSAGING_CHANNEL_TYPES = new Set([
  'facebook_messenger',
  'instagram_dm',
])

function draftKey(conversationId: string, mode: ComposerMode): string {
  return `${DRAFT_PREFIX}:${conversationId}:${mode}`
}

export function getChannelMessageMaxLength(channelType?: string): number | null {
  if (!channelType)
    return null
  return CHANNEL_MESSAGE_MAX_LENGTH[channelType] ?? null
}

export function supportsComposerReplyTo(channelType?: string): boolean {
  return !!channelType && REPLY_TO_CHANNEL_TYPES.has(channelType)
}

export function supportsComposerAttachments(channelType?: string): boolean {
  return !!channelType && ATTACHMENT_CHANNEL_TYPES.has(channelType)
}

export function supportsRichComposer(channelType?: string): boolean {
  return !!channelType && RICH_COMPOSER_CHANNEL_TYPES.has(channelType)
}

export function isMetaMessagingChannel(channelType?: string): boolean {
  return !!channelType && META_MESSAGING_CHANNEL_TYPES.has(channelType)
}

export function loadComposerDraft(conversationId: string, mode: ComposerMode): string {
  if (typeof window === 'undefined' || !conversationId)
    return ''
  try {
    return window.localStorage.getItem(draftKey(conversationId, mode)) || ''
  }
  catch {
    return ''
  }
}

export function saveComposerDraft(conversationId: string, mode: ComposerMode, text: string): void {
  if (typeof window === 'undefined' || !conversationId)
    return
  const key = draftKey(conversationId, mode)
  try {
    const trimmed = text.trim()
    if (!trimmed)
      window.localStorage.removeItem(key)
    else
      window.localStorage.setItem(key, text)
  }
  catch {
    // ignore quota errors
  }
}

export function clearComposerDraft(conversationId: string, mode: ComposerMode): void {
  if (typeof window === 'undefined' || !conversationId)
    return
  try {
    window.localStorage.removeItem(draftKey(conversationId, mode))
  }
  catch {
    // ignore
  }
}

export function loadSendHotkey(): SendHotkey {
  if (typeof window === 'undefined')
    return 'enter'
  const raw = window.localStorage.getItem(SEND_HOTKEY_KEY)
  return raw === 'cmd_enter' ? 'cmd_enter' : 'enter'
}

export function saveSendHotkey(value: SendHotkey): void {
  if (typeof window === 'undefined')
    return
  window.localStorage.setItem(SEND_HOTKEY_KEY, value)
}

export function isMessagingWindowOpen(lastInboundAt?: string): boolean {
  if (!lastInboundAt)
    return false
  const ts = Date.parse(lastInboundAt)
  if (Number.isNaN(ts))
    return false
  return Date.now() - ts <= MESSAGING_WINDOW_MS
}

export function filterCannedResponses(
  items: Array<{ id: string, title: string, content: string, shortcut?: string | null }>,
  query: string,
): Array<{ id: string, title: string, content: string, shortcut?: string | null }> {
  const q = query.trim().toLowerCase()
  if (!q)
    return items.slice(0, 8)
  return items.filter((item) => {
    const shortcut = (item.shortcut || '').toLowerCase()
    return item.title.toLowerCase().includes(q)
      || item.content.toLowerCase().includes(q)
      || (shortcut && shortcut.includes(q))
  }).slice(0, 8)
}

export function extractSlashQuery(text: string, cursor: number): { active: boolean, query: string, start: number } {
  const before = text.slice(0, cursor)
  const slashIndex = before.lastIndexOf('/')
  if (slashIndex < 0)
    return { active: false, query: '', start: -1 }
  if (slashIndex > 0 && before[slashIndex - 1] !== ' ' && before[slashIndex - 1] !== '\n')
    return { active: false, query: '', start: -1 }
  const query = before.slice(slashIndex + 1)
  if (query.includes('\n'))
    return { active: false, query: '', start: -1 }
  return { active: true, query, start: slashIndex }
}

export function applyCannedResponse(text: string, start: number, cursor: number, content: string): { nextText: string, nextCursor: number } {
  const before = text.slice(0, start)
  const after = text.slice(cursor)
  const nextText = `${before}${content}${after}`
  const nextCursor = before.length + content.length
  return { nextText, nextCursor }
}

export function insertAtCursor(text: string, cursor: number, insert: string): { nextText: string, nextCursor: number } {
  const before = text.slice(0, cursor)
  const after = text.slice(cursor)
  return { nextText: `${before}${insert}${after}`, nextCursor: before.length + insert.length }
}

export type TextWrapMark = 'bold' | 'italic' | 'strike'

export function wrapComposerSelection(
  text: string,
  selectionStart: number,
  selectionEnd: number,
  mark: TextWrapMark,
): { nextText: string, nextCursor: number, nextSelectionEnd: number } {
  const selected = text.slice(selectionStart, selectionEnd)
  const wrapper = mark === 'bold' ? '**' : mark === 'italic' ? '*' : '~'
  const wrapped = selected ? `${wrapper}${selected}${wrapper}` : `${wrapper}${wrapper}`
  const before = text.slice(0, selectionStart)
  const after = text.slice(selectionEnd)
  const nextText = `${before}${wrapped}${after}`
  const cursorOffset = selected ? wrapper.length : wrapper.length
  const nextCursor = selectionStart + cursorOffset
  const nextSelectionEnd = nextCursor + (selected ? selected.length : 0)
  return { nextText, nextCursor, nextSelectionEnd }
}

export function supportsComposerFormatting(channelType?: string): boolean {
  return !!channelType && [
    'facebook_messenger',
    'instagram_dm',
    'zalo_oa',
    'zalo_personal',
    'tiktok_messaging',
  ].includes(channelType)
}

export function supportsComposerTyping(channelType?: string): boolean {
  return !!channelType && ['facebook_messenger', 'instagram_dm'].includes(channelType)
}

export function snoozeUntilFromPreset(preset: '1h' | 'tomorrow' | '3d'): string {
  const now = new Date()
  if (preset === '1h') {
    now.setHours(now.getHours() + 1)
    return now.toISOString()
  }
  if (preset === '3d') {
    now.setDate(now.getDate() + 3)
    return now.toISOString()
  }
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  tomorrow.setHours(9, 0, 0, 0)
  return tomorrow.toISOString()
}
