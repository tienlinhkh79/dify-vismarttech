'use client'

import type { Channel, OmnichannelConversation, OmnichannelMessage, OmnichannelRichReplyPayload, OmnichannelSyncJob, ZaloBridgeFailedJob } from '@/service/tools'
import { useTranslation } from '#i18n'
import {
  RiReplyLine,
  RiSearchLine,
} from '@remixicon/react'
import { Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Loading from '@/app/components/base/loading'
// eslint-disable-next-line no-restricted-imports -- omnichannel modals; migrate to Dialog in follow-up
import Modal from '@/app/components/base/modal'
import { toast } from '@/app/components/base/ui/toast'
import { OmnichannelRichComposerPanel } from '@/app/(commonLayout)/omnichannel/omnichannel-rich-composer-panel'
import { OmnichannelMessageContent } from '@/app/(commonLayout)/omnichannel/omnichannel-message-content'
import OmnichannelComposer from '@/app/(commonLayout)/omnichannel/omnichannel-composer'
import {
  supportsComposerAttachments,
  supportsComposerReplyTo,
  supportsRichComposer,
} from '@/app/(commonLayout)/omnichannel/omnichannel-composer-utils'
import { OmnichannelAvatar, SafeRemoteImage } from '@/app/(commonLayout)/omnichannel/omnichannel-remote-image'
import { shouldAttemptRemoteImage } from '@/utils/omnichannel-remote-image'
import { ProviderLogo } from '@/app/components/header/account-setting/channels-ui'
import MemberSelector from '@/app/components/header/account-setting/members-page/transfer-ownership-modal/member-selector'
import { OmnichannelCrmPanel } from '@/app/components/mini-crm/omnichannel-crm-panel'
import { API_PREFIX } from '@/config'
import { useAppContext } from '@/context/app-context'
import Link from '@/next/link'
import { useSearchParams } from '@/next/navigation'
import {

  createOmnichannelConversation,
  getOmnichannelHealth,
  getOmnichannelStats,
  getOmnichannelSyncJob,
  listAllOmnichannelConversations,
  listChannels,
  listOmnichannelCannedResponses,
  listOmnichannelConversations,
  listOmnichannelMessages,
  listZaloBridgeFailedJobs,
  markOmnichannelConversationSeen,
  patchMiniCrmLead,
  patchOmnichannelConversation,
  refreshOmnichannelConversationParticipant,
  retryZaloBridgeJob,
  sendOmnichannelAgentMessage,
  sendOmnichannelInternalNote,
  startOmnichannelHistorySync,
  testOmnichannelWebhook,
  uploadOmnichannelMedia,
} from '@/service/tools'
import { cn } from '@/utils/classnames'
import { resolveConsoleApiBaseHref } from '@/utils/console-api-base'
import { OmnichannelInboxLayout } from './omnichannel-inbox-layout'
import { ALL_INBOXES_ID, OmnichannelInboxSidebar } from './omnichannel-inbox-sidebar'

function omnichannelSseUrl(channelId: string): string {
  const segment = `workspaces/current/channels/${encodeURIComponent(channelId)}/stream`
  const root = resolveConsoleApiBaseHref(API_PREFIX).replace(/\/?$/, '')
  return `${root}/${segment}`
}

type ChannelStats = {
  total_messages: number
  inbound_messages: number
  outbound_messages: number
  active_conversations: number
}

type ChannelHealth = {
  channel_id: string
  enabled: boolean
  channel_type: string
  last_inbound_at?: string
  last_outbound_at?: string
  webhook_path: string
}

const OmnichannelSectionLoading = () => (
  <div className="flex min-h-[12rem] flex-1 items-center justify-center py-8">
    <Loading type="area" />
  </div>
)

function ZaloFailedBridgeJobsSection({ channelId }: { channelId: string }) {
  const { t } = useTranslation()
  const [failedBridgeJobs, setFailedBridgeJobs] = useState<ZaloBridgeFailedJob[]>([])
  const [isLoadingFailedJobs, setIsLoadingFailedJobs] = useState(true)

  useEffect(() => {
    let cancelled = false
    listZaloBridgeFailedJobs(channelId, { limit: 20 })
      .then((res) => {
        if (!cancelled)
          setFailedBridgeJobs(res.data || [])
      })
      .catch(() => {
        if (!cancelled)
          setFailedBridgeJobs([])
      })
      .finally(() => {
        if (!cancelled)
          setIsLoadingFailedJobs(false)
      })
    return () => {
      cancelled = true
    }
  }, [channelId])

  return (
    <section className="border-t border-divider-subtle pt-8">
      <h2 className="mb-3 text-xs font-semibold tracking-wide text-text-quaternary uppercase">{t('settings.omnichannelZaloFailedJobs')}</h2>
      {isLoadingFailedJobs && <p className="text-xs text-text-tertiary">{t('settings.omnichannelZaloFailedJobsLoading')}</p>}
      {!isLoadingFailedJobs && !failedBridgeJobs.length && (
        <p className="text-xs text-text-tertiary">{t('settings.omnichannelZaloFailedJobsEmpty')}</p>
      )}
      {!!failedBridgeJobs.length && (
        <ul className="space-y-2">
          {failedBridgeJobs.map(job => (
            <li key={job.id} className="rounded-lg bg-background-default px-3 py-2 text-xs ring-1 ring-divider-subtle">
              <div className="font-medium text-text-primary">{job.kind}</div>
              <div className="mt-1 line-clamp-2 text-text-tertiary">{job.last_error || '—'}</div>
              <Button
                className="mt-2"
                size="small"
                variant="secondary"
                onClick={() => {
                  void retryZaloBridgeJob(channelId, job.id).then(() => {
                    toast.success(t('settings.omnichannelZaloFailedJobRetryQueued'))
                    return listZaloBridgeFailedJobs(channelId, { limit: 20 })
                  }).then((res) => {
                    setFailedBridgeJobs(res.data || [])
                  })
                }}
              >
                {t('settings.omnichannelZaloFailedJobRetry')}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

const terminalSyncStatuses = new Set(['succeeded', 'failed'])

const isImageUrl = (url: string) => /\.(?:png|jpe?g|gif|webp|bmp|svg)$/i.test(url)

/** PSID / Facebook numeric IDs used as fallback label must not become avatar "initials" (e.g. "32"). */
function omnichannelInitialsSeed(displayNameOrExternalId: string | undefined | null): string {
  const s = (displayNameOrExternalId || '').trim()
  if (!s)
    return ''
  if (/^\d+$/.test(s))
    return ''
  return s
}

/**
 * Newest-first pages from API; we render chronological ascending (oldest → newest).
 *  Fallback poll when SSE is unavailable; primary updates use Redis → SSE.
 */
const OMNICHANNEL_FALLBACK_POLL_MS = 10_000
const OMNICHANNEL_ALL_INBOXES_POLL_MS = 12_000
const OMNICHANNEL_MESSAGES_PAGE_SIZE = 50
const SCROLL_LOAD_OLDER_THRESHOLD_PX = 120
const JUMP_TO_LATEST_DISTANCE_PX = 220
/** Keep pinning to bottom while images and late layout settle (Chatwoot-style). */
const STICK_TO_BOTTOM_AFTER_SWITCH_MS = 2500

const runAfterLayoutPaint = (callback: () => void) => {
  requestAnimationFrame(() => {
    requestAnimationFrame(callback)
  })
}

const sortMessagesChronological = (items: OmnichannelMessage[]) =>
  [...items].sort((a, b) => {
    const aTime = new Date(a.created_at || '').getTime()
    const bTime = new Date(b.created_at || '').getTime()
    if (aTime !== bTime)
      return aTime - bTime
    return String(a.id).localeCompare(String(b.id))
  })

const prependOlderUnique = (older: OmnichannelMessage[], existing: OmnichannelMessage[]) => {
  if (!older.length)
    return existing
  const ids = new Set(existing.map(m => m.id))
  const merged = older.filter(m => !ids.has(m.id))
  return [...merged, ...existing]
}

const mergePollNewer = (freshAsc: OmnichannelMessage[], prev: OmnichannelMessage[]) => {
  if (!freshAsc.length)
    return prev
  const prevIds = new Set(prev.map(m => m.id))
  const additions = freshAsc.filter(m => !prevIds.has(m.id))
  if (!additions.length)
    return prev
  return sortMessagesChronological([...prev, ...additions])
}

const calendarDayKey = (iso?: string) => {
  const d = new Date(iso || '')
  if (Number.isNaN(d.getTime()))
    return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const messageMatchesSearch = (message: OmnichannelMessage, q: string) => {
  const needle = q.trim().toLowerCase()
  if (!needle)
    return true
  const parts = [
    message.content,
    String(message.id),
    message.direction,
    message.source,
    String(message.sender_display_name || ''),
    String(message.channel_actor_name || ''),
    ...(message.attachments || []).map((a) => {
      if (a && typeof a === 'object' && 'url' in a)
        return String((a as { url?: string }).url || '')
      return ''
    }),
  ]
  return parts.join('\n').toLowerCase().includes(needle)
}

type ConversationTab = 'all' | 'open' | 'resolved' | 'pending' | 'snoozed'

const formatOmnichannelListSnippet = (raw: string | undefined | null) => {
  const text = (raw || '').trim().replace(/\s+/g, ' ')
  if (!text)
    return ''
  return text.length > 72 ? `${text.slice(0, 72)}…` : text
}

const conversationMatchesTab = (tab: ConversationTab, c: OmnichannelConversation) => {
  if (tab === 'all')
    return true
  return (c.status || 'open') === tab
}

const conversationStatusLabelKey = (status?: string) => {
  const value = status || 'open'
  const map: Record<string, string> = {
    open: 'settings.omnichannelStatusOpen',
    resolved: 'settings.omnichannelStatusResolved',
    pending: 'settings.omnichannelStatusPending',
    snoozed: 'settings.omnichannelStatusSnoozed',
  }
  return map[value] || 'settings.omnichannelStatusOpen'
}

const isLikelyConversationId = (id: string) => /^[0-9a-f-]{36}$/i.test((id || '').trim())

/** `post()` throws a cloned `Response` on HTTP errors (see `fetch.ts`). */
async function resolveOmnichannelSendError(err: unknown, fallback: string): Promise<string> {
  if (err instanceof Response) {
    const data = (await err.json().catch(() => null)) as { error?: string, message?: string } | null
    return data?.message || data?.error || fallback
  }
  return fallback
}

const OMNICHANNEL_TAB_DEFS: {
  id: ConversationTab
  labelKey: string
  countKey?: keyof { all: number, open: number, resolved: number, pending: number, snoozed: number }
}[] = [
  { id: 'all', labelKey: 'settings.omnichannelTabAll', countKey: 'all' },
  { id: 'open', labelKey: 'settings.omnichannelTabOpen', countKey: 'open' },
  { id: 'resolved', labelKey: 'settings.omnichannelTabResolved', countKey: 'resolved' },
  { id: 'pending', labelKey: 'settings.omnichannelTabPending', countKey: 'pending' },
  { id: 'snoozed', labelKey: 'settings.omnichannelTabSnoozed', countKey: 'snoozed' },
]

const OmnichannelPageContent = () => {
  const searchParams = useSearchParams()
  const urlChannelId = searchParams.get('channel_id') ?? ''
  const urlConversationId = searchParams.get('conversation_id') ?? ''
  const { t, i18n } = useTranslation('common')
  const { userProfile } = useAppContext()
  const dateLocale = i18n.language?.replace('_', '-') || undefined
  const toLocaleText = (value?: string) => {
    if (!value)
      return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime()))
      return value
    return date.toLocaleString(dateLocale)
  }

  const formatListTime = useCallback((iso?: string) => {
    if (!iso)
      return ''
    const d = new Date(iso)
    if (Number.isNaN(d.getTime()))
      return ''
    const diff = Date.now() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1)
      return t('settings.omnichannelRelJustNow')
    if (mins < 60)
      return t('settings.omnichannelRelMins', { count: mins })
    const hours = Math.floor(mins / 60)
    if (hours < 24)
      return t('settings.omnichannelRelHours', { count: hours })
    const days = Math.floor(hours / 24)
    if (days === 1)
      return t('settings.omnichannelDateYesterday')
    if (days < 7)
      return t('settings.omnichannelRelDays', { count: days })
    return d.toLocaleDateString(dateLocale, { month: 'short', day: 'numeric' })
  }, [t, dateLocale])
  const [channels, setChannels] = useState<Channel[]>([])
  const [selectedChannelId, setSelectedChannelId] = useState('')
  const [conversations, setConversations] = useState<OmnichannelConversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState('')
  const [messages, setMessages] = useState<OmnichannelMessage[]>([])
  const [stats, setStats] = useState<ChannelStats | null>(null)
  const [health, setHealth] = useState<ChannelHealth | null>(null)
  const [syncJob, setSyncJob] = useState<OmnichannelSyncJob | null>(null)
  const [syncSince, setSyncSince] = useState('')
  const [syncUntil, setSyncUntil] = useState('')
  const [isPageLoading, setIsPageLoading] = useState(false)
  const [isChannelsLoading, setIsChannelsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isMessagesLoading, setIsMessagesLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isTestingWebhook, setIsTestingWebhook] = useState(false)
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const [composerText, setComposerText] = useState('')
  const [composerAttachmentUrl, setComposerAttachmentUrl] = useState('')
  const [composerAttachmentType, setComposerAttachmentType] = useState<'image' | 'video' | 'audio' | 'file'>('image')
  const [composerAttachmentOpen, setComposerAttachmentOpen] = useState(false)
  const [composerRichOpen, setComposerRichOpen] = useState(false)
  const [composerAttachmentName, setComposerAttachmentName] = useState('')
  const [isUploadingComposerAttachment, setIsUploadingComposerAttachment] = useState(false)
  const [composerAttachmentUploadProgress, setComposerAttachmentUploadProgress] = useState<number | null>(null)
  const [replyToMessage, setReplyToMessage] = useState<OmnichannelMessage | null>(null)
  const composerAttachmentInputRef = useRef<HTMLInputElement | null>(null)
  const [newChatOpen, setNewChatOpen] = useState(false)
  const [newChatUserId, setNewChatUserId] = useState('')
  const [isCreatingChat, setIsCreatingChat] = useState(false)
  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [taskNote, setTaskNote] = useState('')
  const [isSavingTask, setIsSavingTask] = useState(false)
  const [taskLogLines, setTaskLogLines] = useState<{ at: string, text: string }[]>([])
  const syncPollingRef = useRef<number | null>(null)
  const messagesScrollRef = useRef<HTMLDivElement | null>(null)
  const initialScrollToBottomRef = useRef(false)
  const stickToBottomUntilRef = useRef(0)
  const isProgrammaticScrollRef = useRef(false)
  const messagesFetchGenerationRef = useRef(0)
  const allowOlderFromScrollRef = useRef(false)
  const loadOlderInFlightRef = useRef(false)
  const messagesPaginationRef = useRef<{ hasMore: boolean, nextCursor: string | null }>({
    hasMore: false,
    nextCursor: null,
  })
  const [messagesHasMore, setMessagesHasMore] = useState(false)
  const [isLoadingOlderMessages, setIsLoadingOlderMessages] = useState(false)
  const [showJumpToLatest, setShowJumpToLatest] = useState(false)
  const [messageSearchQuery, setMessageSearchQuery] = useState('')
  const [conversationSearchQuery, setConversationSearchQuery] = useState('')
  const [conversationTab, setConversationTab] = useState<ConversationTab>('open')
  const [assigneeFilter, setAssigneeFilter] = useState<'all' | 'mine' | 'unassigned'>('all')
  const [crmRefreshKey, setCrmRefreshKey] = useState(0)
  const [composerInternalNote, setComposerInternalNote] = useState(false)
  const [cannedResponses, setCannedResponses] = useState<Array<{ id: string, title: string, content: string }>>([])
  const refreshCannedResponses = useCallback(() => {
    listOmnichannelCannedResponses()
      .then(res => setCannedResponses(res.data || []))
      .catch(() => setCannedResponses([]))
  }, [])
  const [channelHealthById, setChannelHealthById] = useState<Record<string, ChannelHealth>>({})
  const messengerParticipantRefreshAttemptedRef = useRef('')
  const markSeenAttemptedRef = useRef('')
  const selectedChannelIdRef = useRef('')
  const selectedConversationIdRef = useRef('')
  const isMessagesLoadingRef = useRef(false)
  const isLoadingOlderMessagesRef = useRef(false)
  const omnichannelRealtimeDebounceRef = useRef<number | null>(null)
  const pendingDeepConversationIdRef = useRef<string | null>(null)

  useEffect(() => {
    selectedChannelIdRef.current = selectedChannelId
  }, [selectedChannelId])

  useEffect(() => {
    selectedConversationIdRef.current = selectedConversationId
  }, [selectedConversationId])

  useEffect(() => {
    isMessagesLoadingRef.current = isMessagesLoading
  }, [isMessagesLoading])

  useEffect(() => {
    isLoadingOlderMessagesRef.current = isLoadingOlderMessages
  }, [isLoadingOlderMessages])

  useEffect(() => {
    queueMicrotask(() => setTaskLogLines([]))
  }, [selectedConversationId])

  useEffect(() => {
    queueMicrotask(() => setIsChannelsLoading(true))
    ;(async () => {
      try {
        const response = await listChannels({ include_branding: false })
        const nextChannels = response.data || []
        setChannels(nextChannels)
        const deepChannel = urlChannelId.trim()
        const deepConv = urlConversationId.trim()
        if (deepChannel && nextChannels.some(c => c.channel_id === deepChannel)) {
          setSelectedChannelId(deepChannel)
          if (deepConv)
            pendingDeepConversationIdRef.current = deepConv
        }
        else if (nextChannels.length > 0) {
          setSelectedChannelId(ALL_INBOXES_ID)
        }
      }
      catch {
        setError(t('settings.omnichannelErrorLoadChannels'))
      }
      finally {
        setIsChannelsLoading(false)
      }
    })()
  }, [t, i18n.language, urlChannelId, urlConversationId])

  const isAllInboxes = selectedChannelId === ALL_INBOXES_ID

  const conversationListParams = useCallback(() => {
    const status = conversationTab === 'all' ? undefined : conversationTab
    const base = {
      limit: 50,
      status,
      ...(assigneeFilter === 'unassigned' ? { unassigned_only: true } : {}),
      ...(assigneeFilter === 'mine' && userProfile.id ? { assignee_account_id: userProfile.id } : {}),
    }
    return base
  }, [assigneeFilter, conversationTab, userProfile.id])

  useEffect(() => {
    if (!channels.length)
      return
    let cancelled = false
    let idleHandle: number | undefined
    let timeoutHandle: number | undefined

    const loadHealthInBatches = async () => {
      const healthMap: Record<string, ChannelHealth> = {}
      const ids = channels.map(ch => ch.channel_id).filter(Boolean)
      const batchSize = 2
      for (let i = 0; i < ids.length; i += batchSize) {
        if (cancelled)
          return
        const batch = ids.slice(i, i + batchSize)
        const entries = await Promise.all(
          batch.map(async (channelId) => {
            try {
              const res = await getOmnichannelHealth(channelId)
              return [channelId, res.data] as const
            }
            catch {
              return [channelId, undefined] as const
            }
          }),
        )
        for (const [channelId, health] of entries) {
          if (health)
            healthMap[channelId] = health
        }
        if (!cancelled)
          setChannelHealthById({ ...healthMap })
        // Yield so the inbox UI can paint between batches.
        await new Promise<void>(resolve => window.setTimeout(resolve, 0))
      }
    }

    const start = () => {
      void loadHealthInBatches()
    }

    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      idleHandle = window.requestIdleCallback(start, { timeout: 2500 })
    }
    else {
      timeoutHandle = window.setTimeout(start, 800)
    }

    return () => {
      cancelled = true
      if (idleHandle != null && typeof window !== 'undefined' && 'cancelIdleCallback' in window)
        window.cancelIdleCallback(idleHandle)
      if (timeoutHandle != null)
        window.clearTimeout(timeoutHandle)
    }
  }, [channels])

  useEffect(() => {
    refreshCannedResponses()
  }, [refreshCannedResponses])

  useEffect(() => {
    if (!selectedChannelId)
      return

    queueMicrotask(() => {
      setIsPageLoading(true)
      setError('')
    })
    ;(async () => {
      try {
        const listParams = conversationListParams()
        const conversationRes = isAllInboxes
          ? await listAllOmnichannelConversations(listParams)
          : await listOmnichannelConversations(selectedChannelId, listParams)
        const nextConversations = conversationRes.data || []
        setConversations(nextConversations)
        setSelectedConversationId((prev) => {
          const pending = pendingDeepConversationIdRef.current
          if (pending && nextConversations.some(item => item.id === pending)) {
            pendingDeepConversationIdRef.current = null
            return pending
          }
          if (prev && nextConversations.some(item => item.id === prev))
            return prev
          return nextConversations[0]?.id || ''
        })
        if (!isAllInboxes) {
          const [statsRes, healthRes] = await Promise.all([
            getOmnichannelStats(selectedChannelId),
            getOmnichannelHealth(selectedChannelId),
          ])
          setStats(statsRes.data)
          setHealth(healthRes.data)
        }
        else {
          setStats(null)
          setHealth(null)
        }
      }
      catch {
        setError(t('settings.omnichannelErrorLoadData'))
      }
      finally {
        setIsPageLoading(false)
      }
    })()
  }, [selectedChannelId, t, i18n.language, isAllInboxes, conversationListParams])

  const selectedConversation = useMemo(
    () => conversations.find(item => item.id === selectedConversationId),
    [conversations, selectedConversationId],
  )

  const activeMessageChannelId = useMemo(() => {
    if (!isAllInboxes)
      return selectedChannelId
    return selectedConversation?.channel_id || ''
  }, [isAllInboxes, selectedChannelId, selectedConversation?.channel_id])

  useEffect(() => {
    if (!activeMessageChannelId || !selectedConversationId)
      return
    const channel = channels.find(c => c.channel_id === activeMessageChannelId)
    if (!channel || channel.channel_type !== 'facebook_messenger')
      return
    const conv = conversations.find(c => c.id === selectedConversationId)
    if (!conv)
      return
    // Meta CDN avatars are not loaded in the browser; only refresh when the display name is missing.
    const hasName = !!(conv.participant_display_name || '').trim()
    if (hasName)
      return
    if (messengerParticipantRefreshAttemptedRef.current === selectedConversationId)
      return
    messengerParticipantRefreshAttemptedRef.current = selectedConversationId

    let cancelled = false
    void (async () => {
      try {
        const res = await refreshOmnichannelConversationParticipant(activeMessageChannelId, selectedConversationId)
        const updated = res.data
        if (cancelled || !updated?.id)
          return
        setConversations(prev => prev.map(c => (c.id === updated.id ? { ...c, ...updated } : c)))
      }
      catch {
        /* Meta may return empty profile; UI keeps initials */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [activeMessageChannelId, selectedConversationId, channels, conversations])

  useEffect(() => {
    if (!activeMessageChannelId || !selectedConversationId || !isLikelyConversationId(selectedConversationId))
      return
    // Avoid 404 spam when deep-link / stale selection is not in the loaded inbox list.
    const conv = conversations.find(c => c.id === selectedConversationId)
    if (!conv || conv.channel_id !== activeMessageChannelId)
      return
    const seenKey = `${activeMessageChannelId}:${selectedConversationId}`
    if (markSeenAttemptedRef.current === seenKey)
      return
    markSeenAttemptedRef.current = seenKey
    void markOmnichannelConversationSeen(activeMessageChannelId, selectedConversationId)
      .then((res) => {
        setConversations(prev => prev.map(c => c.id === selectedConversationId ? { ...c, ...res.data, unread_count: 0 } : c))
      })
      .catch(() => {
        // Allow one retry later if the conversation was not ready yet.
        if (markSeenAttemptedRef.current === seenKey)
          markSeenAttemptedRef.current = ''
      })
  }, [activeMessageChannelId, selectedConversationId, conversations])

  useEffect(() => {
    if (!activeMessageChannelId || !selectedConversationId)
      return

    const fetchGeneration = messagesFetchGenerationRef.current + 1
    messagesFetchGenerationRef.current = fetchGeneration
    initialScrollToBottomRef.current = true
    stickToBottomUntilRef.current = Date.now() + STICK_TO_BOTTOM_AFTER_SWITCH_MS
    allowOlderFromScrollRef.current = false
    setMessageSearchQuery('')
    setMessages([])
    setMessagesHasMore(false)
    messagesPaginationRef.current = { hasMore: false, nextCursor: null }
    setShowJumpToLatest(false)
    setIsMessagesLoading(true)

    listOmnichannelMessages(activeMessageChannelId, selectedConversationId, { limit: OMNICHANNEL_MESSAGES_PAGE_SIZE })
      .then((res) => {
        if (messagesFetchGenerationRef.current !== fetchGeneration)
          return
        const asc = sortMessagesChronological(res.data || [])
        setMessages(asc)
        const hasMore = !!res.has_more
        const nextCur = res.next_cursor ?? null
        setMessagesHasMore(hasMore)
        messagesPaginationRef.current = { hasMore, nextCursor: nextCur }
      })
      .catch(() => {
        if (messagesFetchGenerationRef.current !== fetchGeneration)
          return
        setMessages([])
        setMessagesHasMore(false)
        messagesPaginationRef.current = { hasMore: false, nextCursor: null }
      })
      .finally(() => {
        if (messagesFetchGenerationRef.current !== fetchGeneration)
          return
        setIsMessagesLoading(false)
      })
  }, [activeMessageChannelId, selectedConversationId])

  const loadOlderMessages = useCallback(async () => {
    if (!activeMessageChannelId || !selectedConversationId)
      return
    if (loadOlderInFlightRef.current)
      return
    const { hasMore, nextCursor } = messagesPaginationRef.current
    if (!hasMore || nextCursor == null)
      return

    const el = messagesScrollRef.current
    if (!el)
      return

    loadOlderInFlightRef.current = true
    setIsLoadingOlderMessages(true)
    const prevHeight = el.scrollHeight
    const prevTop = el.scrollTop

    try {
      const res = await listOmnichannelMessages(activeMessageChannelId, selectedConversationId, {
        limit: OMNICHANNEL_MESSAGES_PAGE_SIZE,
        cursor: nextCursor,
      })
      const olderAsc = sortMessagesChronological(res.data || [])
      setMessages(prev => prependOlderUnique(olderAsc, prev))
      const nextHas = !!res.has_more
      const nextCur = res.next_cursor ?? null
      setMessagesHasMore(nextHas)
      messagesPaginationRef.current = { hasMore: nextHas, nextCursor: nextCur }
      runAfterLayoutPaint(() => {
        const node = messagesScrollRef.current
        if (!node)
          return
        isProgrammaticScrollRef.current = true
        node.scrollTop = node.scrollHeight - prevHeight + prevTop
      })
    }
    catch {
      // keep scroll position; user can scroll again to retry
    }
    finally {
      setIsLoadingOlderMessages(false)
      loadOlderInFlightRef.current = false
    }
  }, [activeMessageChannelId, selectedConversationId])

  const scrollMessagesToBottom = useCallback((smooth: boolean) => {
    const el = messagesScrollRef.current
    if (!el)
      return
    isProgrammaticScrollRef.current = true
    if (smooth) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    }
    else {
      el.scrollTop = el.scrollHeight
      runAfterLayoutPaint(() => {
        const node = messagesScrollRef.current
        if (node)
          node.scrollTop = node.scrollHeight
      })
    }
    setShowJumpToLatest(false)
  }, [])

  const refreshChannelData = useCallback(async (opts?: { includeMessages?: boolean }) => {
    const channelId = selectedChannelIdRef.current
    if (!channelId)
      return
    if (typeof document !== 'undefined' && document.hidden)
      return

    const allInboxes = channelId === ALL_INBOXES_ID
    let resolvedConversationId = selectedConversationIdRef.current
    try {
      const listParams = conversationListParams()
      const conversationRes = allInboxes
        ? await listAllOmnichannelConversations(listParams)
        : await listOmnichannelConversations(channelId, listParams)
      const nextConversations = conversationRes.data || []
      const prevSel = selectedConversationIdRef.current
      resolvedConversationId = (prevSel && nextConversations.some(item => item.id === prevSel))
        ? prevSel
        : (nextConversations[0]?.id || '')
      setConversations(nextConversations)
      setSelectedConversationId(resolvedConversationId)
      selectedConversationIdRef.current = resolvedConversationId
      if (!allInboxes) {
        const [statsRes, healthRes] = await Promise.all([
          getOmnichannelStats(channelId),
          getOmnichannelHealth(channelId),
        ])
        setStats(statsRes.data)
        setHealth(healthRes.data)
      }
    }
    catch {
      // avoid flashing the main error banner on transient failures
    }

    if (!opts?.includeMessages)
      return
    const convId = resolvedConversationId
    if (!convId)
      return
    const messageChannelId = allInboxes
      ? (conversations.find(c => c.id === convId)?.channel_id || '')
      : channelId
    if (!messageChannelId)
      return
    if (loadOlderInFlightRef.current)
      return
    if (isMessagesLoadingRef.current || isLoadingOlderMessagesRef.current)
      return

    const el = messagesScrollRef.current
    const nearBottom = el
      ? el.scrollHeight - el.scrollTop - el.clientHeight < 88
      : true
    try {
      const res = await listOmnichannelMessages(messageChannelId, convId, {
        limit: OMNICHANNEL_MESSAGES_PAGE_SIZE,
      })
      const asc = sortMessagesChronological(res.data || [])
      let grew = false
      setMessages((prev) => {
        const next = mergePollNewer(asc, prev)
        grew = next.length > prev.length
        return next
      })
      if (nearBottom && grew)
        setTimeout(() => scrollMessagesToBottom(false), 0)
    }
    catch {
      // ignore transient errors
    }
  }, [scrollMessagesToBottom, conversationListParams, conversations])

  const scheduleOmnichannelRealtimeRefresh = useCallback(() => {
    if (omnichannelRealtimeDebounceRef.current)
      window.clearTimeout(omnichannelRealtimeDebounceRef.current)
    omnichannelRealtimeDebounceRef.current = window.setTimeout(() => {
      omnichannelRealtimeDebounceRef.current = null
      void refreshChannelData({ includeMessages: true })
    }, 400)
  }, [refreshChannelData])

  const onMessagesScroll = useCallback(() => {
    const el = messagesScrollRef.current
    if (!el)
      return
    if (isProgrammaticScrollRef.current) {
      isProgrammaticScrollRef.current = false
      return
    }
    stickToBottomUntilRef.current = 0
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    setShowJumpToLatest(distanceFromBottom > JUMP_TO_LATEST_DISTANCE_PX)
    if (!allowOlderFromScrollRef.current)
      return
    if (el.scrollTop > SCROLL_LOAD_OLDER_THRESHOLD_PX)
      return
    const { hasMore, nextCursor } = messagesPaginationRef.current
    if (!hasMore || nextCursor == null || loadOlderInFlightRef.current)
      return
    void loadOlderMessages()
  }, [loadOlderMessages])

  /** Slow fallback when SSE is down; push path is Redis → API SSE. */
  useEffect(() => {
    if (!selectedChannelId)
      return
    const pollMs = selectedChannelId === ALL_INBOXES_ID
      ? OMNICHANNEL_ALL_INBOXES_POLL_MS
      : OMNICHANNEL_FALLBACK_POLL_MS
    const intervalId = window.setInterval(() => {
      // Keep fallback light: conversation list only. Message sync comes from SSE.
      void refreshChannelData({ includeMessages: false })
    }, pollMs)
    return () => window.clearInterval(intervalId)
  }, [selectedChannelId, refreshChannelData])

  /** Subscribe to server push (Redis → SSE). Prefer one stream for the active channel. */
  useEffect(() => {
    if (!selectedChannelId)
      return
    if (typeof window === 'undefined' || typeof EventSource === 'undefined')
      return

    const channelIds = selectedChannelId === ALL_INBOXES_ID
      ? (activeMessageChannelId ? [activeMessageChannelId] : [])
      : [selectedChannelId]
    if (!channelIds.length)
      return

    let cancelled = false
    const sources = new Map<string, EventSource>()
    const reconnectTimers = new Map<string, number>()

    const clearReconnect = (channelId: string) => {
      const timer = reconnectTimers.get(channelId)
      if (timer != null) {
        window.clearTimeout(timer)
        reconnectTimers.delete(channelId)
      }
    }

    const connectChannel = (channelId: string) => {
      if (cancelled)
        return
      clearReconnect(channelId)
      const existing = sources.get(channelId)
      if (existing) {
        existing.close()
        sources.delete(channelId)
      }
      const es = new EventSource(omnichannelSseUrl(channelId), { withCredentials: true })
      sources.set(channelId, es)
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as { type?: string }
          if (data.type === 'connected')
            return
          if (data.type !== 'omnichannel')
            return
          scheduleOmnichannelRealtimeRefresh()
        }
        catch {
          /* ignore non-JSON */
        }
      }
      es.onerror = () => {
        es.close()
        sources.delete(channelId)
        if (cancelled)
          return
        clearReconnect(channelId)
        reconnectTimers.set(channelId, window.setTimeout(() => connectChannel(channelId), 5000))
      }
    }

    for (const channelId of channelIds)
      connectChannel(channelId)

    return () => {
      cancelled = true
      for (const channelId of reconnectTimers.keys())
        clearReconnect(channelId)
      for (const es of sources.values())
        es.close()
      sources.clear()
      if (omnichannelRealtimeDebounceRef.current) {
        window.clearTimeout(omnichannelRealtimeDebounceRef.current)
        omnichannelRealtimeDebounceRef.current = null
      }
    }
  }, [selectedChannelId, activeMessageChannelId, scheduleOmnichannelRealtimeRefresh])

  /** Refresh when the tab becomes visible again (mobile / alt-tab). */
  useEffect(() => {
    const onVisibility = () => {
      if (!document.hidden)
        void refreshChannelData({ includeMessages: true })
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [refreshChannelData])

  useLayoutEffect(() => {
    if (!initialScrollToBottomRef.current)
      return
    if (isMessagesLoading)
      return
    const el = messagesScrollRef.current
    if (!el)
      return
    if (messages.length === 0) {
      initialScrollToBottomRef.current = false
      allowOlderFromScrollRef.current = true
      return
    }
    const pinToBottom = () => {
      const node = messagesScrollRef.current
      if (!node)
        return
      isProgrammaticScrollRef.current = true
      node.scrollTop = node.scrollHeight
    }
    pinToBottom()
    runAfterLayoutPaint(() => {
      pinToBottom()
      initialScrollToBottomRef.current = false
      allowOlderFromScrollRef.current = true
    })
  }, [isMessagesLoading, messages.length, selectedConversationId])

  useEffect(() => {
    if (!selectedConversationId || isMessagesLoading)
      return
    const el = messagesScrollRef.current
    if (!el)
      return

    const pinIfNeeded = () => {
      if (initialScrollToBottomRef.current || Date.now() < stickToBottomUntilRef.current) {
        isProgrammaticScrollRef.current = true
        el.scrollTop = el.scrollHeight
      }
    }

    const observer = new ResizeObserver(pinIfNeeded)
    observer.observe(el)
    pinIfNeeded()

    return () => observer.disconnect()
  }, [isMessagesLoading, messages.length, selectedConversationId])

  useEffect(() => {
    return () => {
      if (syncPollingRef.current)
        window.clearInterval(syncPollingRef.current)
    }
  }, [])

  const channelTypeLabel = (channelType?: string) => {
    switch (channelType) {
      case 'facebook_messenger':
        return t('settings.channelsProviderDisplayMessenger')
      case 'instagram_dm':
        return t('settings.channelsProviderDisplayInstagram')
      case 'tiktok_messaging':
        return t('settings.channelsProviderDisplayTikTok')
      case 'zalo_oa':
        return t('settings.channelsProviderDisplayZalo')
      case 'website_widget':
        return t('settings.channelsProviderDisplayWebsite')
      default:
        return channelType?.replace(/_/g, ' ') ?? ''
    }
  }

  const syncJobStatusLabel = (status: string) => {
    const keyMap: Record<string, string> = {
      pending: 'settings.omnichannelJobStatusPending',
      running: 'settings.omnichannelJobStatusRunning',
      succeeded: 'settings.omnichannelJobStatusSucceeded',
      failed: 'settings.omnichannelJobStatusFailed',
    }
    const key = keyMap[status]
    return key ? t(key as never) : status
  }

  const messageDirectionAndSource = (direction: string, source: string, metadata?: Record<string, unknown>) => {
    const dir = direction === 'inbound'
      ? t('settings.omnichannelDirectionInbound')
      : t('settings.omnichannelDirectionOutbound')
    const inboxConsole = Boolean(metadata && typeof metadata === 'object' && metadata.inbox_console)
    if (inboxConsole && direction === 'outbound')
      return `${dir} · ${t('settings.omnichannelSourceInbox')}`
    const srcMap: Record<string, string> = {
      webhook: 'settings.omnichannelSourceWebhook',
      sync: 'settings.omnichannelSourceSync',
      system: 'settings.omnichannelSourceSystem',
      internal_note: 'settings.omnichannelSourceInternalNote',
      agent: 'settings.omnichannelSourceAgent',
      web_app: 'settings.omnichannelSourceWebApp',
    }
    const srcKey = srcMap[source]
    const src = srcKey ? t(srcKey as never) : source
    return `${dir} · ${src}`
  }

  const formatDayDividerLabel = useCallback((iso?: string) => {
    const d = new Date(iso || '')
    if (Number.isNaN(d.getTime()))
      return ''
    const now = new Date()
    const startOf = (x: Date) => {
      const c = new Date(x)
      c.setHours(0, 0, 0, 0)
      return c.getTime()
    }
    const diffDays = Math.round((startOf(now) - startOf(d)) / 86400000)
    if (diffDays === 0)
      return t('settings.omnichannelDateToday')
    if (diffDays === 1)
      return t('settings.omnichannelDateYesterday')
    const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
    if (d.getFullYear() !== now.getFullYear())
      opts.year = 'numeric'
    return d.toLocaleDateString(dateLocale, opts)
  }, [dateLocale, t])

  type TimelineItem
    = | { kind: 'divider', key: string, label: string }
      | { kind: 'message', key: string, message: OmnichannelMessage }

  const messageTimelineItems = useMemo((): TimelineItem[] => {
    const q = messageSearchQuery.trim().toLowerCase()
    const base = q ? messages.filter(m => messageMatchesSearch(m, q)) : messages
    const out: TimelineItem[] = []
    let lastDay = ''
    for (const message of base) {
      const dk = calendarDayKey(message.created_at)
      if (dk && dk !== lastDay) {
        lastDay = dk
        out.push({
          kind: 'divider',
          key: `div-${dk}`,
          label: formatDayDividerLabel(message.created_at),
        })
      }
      out.push({ kind: 'message', key: String(message.id), message })
    }
    return out
  }, [messages, messageSearchQuery, formatDayDividerLabel])

  const selectedChannel = useMemo(() => {
    if (isAllInboxes) {
      const convChannelId = selectedConversation?.channel_id
      if (convChannelId)
        return channels.find(item => item.channel_id === convChannelId)
      return undefined
    }
    if (selectedChannelId === ALL_INBOXES_ID)
      return undefined
    return channels.find(item => item.channel_id === selectedChannelId)
  }, [channels, isAllInboxes, selectedChannelId, selectedConversation?.channel_id])

  const selectedCrmVertical = selectedChannel?.mini_crm_business_line === 'nail' ? 'nail' : 'restaurant'

  const activeChannelType = selectedConversation?.channel_type || selectedChannel?.channel_type
  const isZaloOaChannel = activeChannelType === 'zalo_oa'

  const isInboxBootstrapLoading = isChannelsLoading || (!!selectedChannelId && isPageLoading)

  const supportsComposerAttachmentsFlag = useMemo(
    () => supportsComposerAttachments(activeChannelType),
    [activeChannelType],
  )

  const supportsRichComposerFlag = useMemo(
    () => supportsRichComposer(activeChannelType),
    [activeChannelType],
  )

  const lastInboundAt = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i]?.direction === 'inbound')
        return messages[i].created_at
    }
    return undefined
  }, [messages])

  const canSendComposer = useMemo(
    () => !!(composerText.trim() || composerAttachmentUrl.trim()),
    [composerAttachmentUrl, composerText],
  )

  const isMetaHistorySyncSupported = useMemo(() => {
    const ct = activeChannelType
    return ct === 'facebook_messenger' || ct === 'instagram_dm'
  }, [activeChannelType])

  const unreadByChannelId = useMemo(() => {
    const out: Record<string, number> = {}
    for (const c of conversations) {
      const n = c.unread_count || 0
      if (n > 0)
        out[c.channel_id] = (out[c.channel_id] || 0) + n
    }
    return out
  }, [conversations])

  const filteredConversations = useMemo(() => {
    const q = conversationSearchQuery.trim().toLowerCase()
    return conversations.filter((c) => {
      if (!conversationMatchesTab(conversationTab, c))
        return false
      if (!q)
        return true
      const name = (c.participant_display_name || '').trim().toLowerCase()
      const ext = (c.external_user_id || '').toLowerCase()
      return name.includes(q) || ext.includes(q)
    })
  }, [conversations, conversationSearchQuery, conversationTab])

  const tabCounts = useMemo(() => ({
    all: conversations.length,
    open: conversations.filter(c => conversationMatchesTab('open', c)).length,
    resolved: conversations.filter(c => conversationMatchesTab('resolved', c)).length,
    pending: conversations.filter(c => conversationMatchesTab('pending', c)).length,
    snoozed: conversations.filter(c => conversationMatchesTab('snoozed', c)).length,
  }), [conversations])

  const lastMessagePreview = useMemo(() => {
    if (!messages.length)
      return ''
    const last = messages[messages.length - 1]
    const text = (last.content || '').trim().replace(/\s+/g, ' ')
    if (!text)
      return ''
    return text.length > 72 ? `${text.slice(0, 72)}…` : text
  }, [messages])

  const imageAttachments = useMemo(() => {
    return messages
      .flatMap(item => (item.attachments || [])
        .map((attachment) => {
          const url = typeof attachment.url === 'string' ? attachment.url : ''
          return { id: item.id, url, direction: item.direction }
        }))
      .filter(item => !!item.url && isImageUrl(item.url) && shouldAttemptRemoteImage(item.url))
      .slice(-6)
      .reverse()
  }, [messages])

  const onStartSync = async () => {
    if (!selectedChannelId)
      return
    setIsSyncing(true)
    setError('')
    try {
      const payload: { since?: string, until?: string } = {}
      if (syncSince)
        payload.since = new Date(syncSince).toISOString()
      if (syncUntil)
        payload.until = new Date(syncUntil).toISOString()
      const response = await startOmnichannelHistorySync(selectedChannelId, payload)
      const createdJob = response.data
      setSyncJob(createdJob)
      if (syncPollingRef.current)
        window.clearInterval(syncPollingRef.current)

      syncPollingRef.current = window.setInterval(async () => {
        try {
          const polled = await getOmnichannelSyncJob(selectedChannelId, createdJob.id)
          const nextJob = polled.data
          setSyncJob(nextJob)
          if (terminalSyncStatuses.has(nextJob.status)) {
            if (syncPollingRef.current)
              window.clearInterval(syncPollingRef.current)
            syncPollingRef.current = null
            await refreshChannelData({ includeMessages: true })
            setIsSyncing(false)
            if (nextJob.status === 'failed')
              setError(nextJob.last_error || t('settings.omnichannelErrorSyncFailed'))
          }
        }
        catch {
          if (syncPollingRef.current)
            window.clearInterval(syncPollingRef.current)
          syncPollingRef.current = null
          setIsSyncing(false)
          setError(t('settings.omnichannelErrorPollSync'))
        }
      }, 2000)
    }
    catch {
      setError(t('settings.omnichannelErrorStartSync'))
      setIsSyncing(false)
    }
  }

  const onWebhookTest = async () => {
    if (!selectedChannelId)
      return
    setIsTestingWebhook(true)
    setError('')
    try {
      await testOmnichannelWebhook(selectedChannelId)
      const healthRes = await getOmnichannelHealth(selectedChannelId)
      setHealth(healthRes.data)
    }
    catch {
      setError(t('settings.omnichannelErrorWebhookTest'))
    }
    finally {
      setIsTestingWebhook(false)
    }
  }

  const onSendRichComposer = async (replyPayload: OmnichannelRichReplyPayload) => {
    if (!activeMessageChannelId || !selectedConversationId)
      return
    setIsSendingMessage(true)
    setError('')
    try {
      await sendOmnichannelAgentMessage(activeMessageChannelId, selectedConversationId, {
        reply_payload: replyPayload,
        ...(replyToMessage?.id ? { quote_message_id: replyToMessage.id } : {}),
      })
      setComposerRichOpen(false)
      setReplyToMessage(null)
      const res = await listOmnichannelMessages(activeMessageChannelId, selectedConversationId, {
        limit: OMNICHANNEL_MESSAGES_PAGE_SIZE,
      })
      setMessages(sortMessagesChronological(res.data || []))
      setMessagesHasMore(!!res.has_more)
      messagesPaginationRef.current = {
        hasMore: !!res.has_more,
        nextCursor: res.next_cursor ?? null,
      }
      void refreshChannelData({ includeMessages: false })
      toast.success(t('settings.omnichannelRichComposerSendSuccess'))
    }
    catch (err) {
      setError(await resolveOmnichannelSendError(err, t('settings.omnichannelSendError')))
    }
    finally {
      setIsSendingMessage(false)
    }
  }

  const onSendComposer = async () => {
    if (!activeMessageChannelId || !selectedConversationId)
      return
    const text = composerText.trim()
    const attUrl = composerAttachmentUrl.trim()
    if (!text && !attUrl) {
      toast.error(t('settings.omnichannelComposerValidationEmpty'))
      return
    }
    if (composerInternalNote) {
      if (!text) {
        toast.error(t('settings.omnichannelInternalNoteValidationEmpty'))
        return
      }
      setIsSendingMessage(true)
      setError('')
      try {
        await sendOmnichannelInternalNote(activeMessageChannelId, selectedConversationId, { text })
        setComposerText('')
        setComposerInternalNote(false)
        const res = await listOmnichannelMessages(activeMessageChannelId, selectedConversationId, {
          limit: OMNICHANNEL_MESSAGES_PAGE_SIZE,
        })
        setMessages(sortMessagesChronological(res.data || []))
        toast.success(t('settings.omnichannelInternalNoteSaved'))
      }
      catch {
        toast.error(t('settings.omnichannelSendError'))
      }
      finally {
        setIsSendingMessage(false)
      }
      return
    }
    if (attUrl && !supportsComposerAttachmentsFlag) {
      toast.error(t('settings.omnichannelComposerAttachmentUnsupported'))
      return
    }
    setIsSendingMessage(true)
    setError('')
    try {
      await sendOmnichannelAgentMessage(activeMessageChannelId, selectedConversationId, {
        text,
        ...(attUrl
          ? { attachment_url: attUrl, attachment_type: composerAttachmentType }
          : {}),
        ...(replyToMessage?.id ? { quote_message_id: replyToMessage.id } : {}),
      })
      setComposerText('')
      setReplyToMessage(null)
      setComposerAttachmentUrl('')
      setComposerAttachmentName('')
      setComposerAttachmentUploadProgress(null)
      setComposerAttachmentOpen(false)
      const res = await listOmnichannelMessages(activeMessageChannelId, selectedConversationId, {
        limit: OMNICHANNEL_MESSAGES_PAGE_SIZE,
      })
      setMessages(sortMessagesChronological(res.data || []))
      setMessagesHasMore(!!res.has_more)
      messagesPaginationRef.current = {
        hasMore: !!res.has_more,
        nextCursor: res.next_cursor ?? null,
      }
      void refreshChannelData({ includeMessages: false })
      toast.success(t('settings.omnichannelSendSuccess'))
    }
    catch (err) {
      setError(await resolveOmnichannelSendError(err, t('settings.omnichannelSendError')))
    }
    finally {
      setIsSendingMessage(false)
    }
  }

  const onResolveConversation = async () => {
    if (!activeMessageChannelId || !selectedConversationId)
      return
    try {
      const res = await patchOmnichannelConversation(activeMessageChannelId, selectedConversationId, {
        status: 'resolved',
      })
      setConversations(prev => prev.map(c => c.id === selectedConversationId ? { ...c, ...res.data } : c))
      setCrmRefreshKey(prev => prev + 1)
      toast.success(t('settings.omnichannelResolvedSuccess'))
    }
    catch {
      toast.error(t('settings.omnichannelResolvedError'))
    }
  }

  const onReopenConversation = async () => {
    if (!activeMessageChannelId || !selectedConversationId)
      return
    try {
      const res = await patchOmnichannelConversation(activeMessageChannelId, selectedConversationId, {
        status: 'open',
      })
      setConversations(prev => prev.map(c => c.id === selectedConversationId ? { ...c, ...res.data } : c))
      setCrmRefreshKey(prev => prev + 1)
      toast.success(t('settings.omnichannelReopenedSuccess'))
    }
    catch {
      toast.error(t('settings.omnichannelReopenedError'))
    }
  }

  const onAssignConversation = async (accountId: string | null) => {
    if (!activeMessageChannelId || !selectedConversationId)
      return
    try {
      const res = await patchOmnichannelConversation(
        activeMessageChannelId,
        selectedConversationId,
        accountId
          ? { assignee_account_id: accountId }
          : { clear_assignee: true },
      )
      setConversations(prev => prev.map(c => c.id === selectedConversationId ? { ...c, ...res.data } : c))
      setCrmRefreshKey(prev => prev + 1)
      toast.success(t('settings.omnichannelAssigneeUpdated'))
    }
    catch {
      toast.error(t('settings.omnichannelAssigneeUpdateError'))
    }
  }

  const clearComposerAttachment = useCallback(() => {
    setComposerAttachmentUrl('')
    setComposerAttachmentName('')
    setComposerAttachmentUploadProgress(null)
    if (composerAttachmentInputRef.current)
      composerAttachmentInputRef.current.value = ''
  }, [])

  const onComposerAttachmentFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file)
      return
    await uploadComposerAttachmentFile(file)
  }

  const uploadComposerAttachmentFile = async (file: File) => {
    setIsUploadingComposerAttachment(true)
    setComposerAttachmentUploadProgress(0)
    setComposerAttachmentName(file.name)
    setError('')
    try {
      const uploaded = await uploadOmnichannelMedia(file, percent => setComposerAttachmentUploadProgress(percent))
      setComposerAttachmentUrl(uploaded.url)
      setComposerAttachmentType(uploaded.attachment_type)
      setComposerAttachmentName(uploaded.name)
      setComposerAttachmentOpen(true)
      toast.success(t('settings.omnichannelComposerUploadSuccess'))
    }
    catch {
      clearComposerAttachment()
      toast.error(t('settings.omnichannelComposerUploadError'))
    }
    finally {
      setIsUploadingComposerAttachment(false)
      setComposerAttachmentUploadProgress(null)
      if (composerAttachmentInputRef.current)
        composerAttachmentInputRef.current.value = ''
    }
  }


  const submitNewChat = async () => {
    if (!selectedChannelId) {
      toast.error(t('settings.omnichannelErrorLoadChannels'))
      return
    }
    const ext = newChatUserId.trim()
    if (!ext) {
      toast.error(t('settings.omnichannelNewChatUserIdRequired'))
      return
    }
    setIsCreatingChat(true)
    setError('')
    try {
      const res = await createOmnichannelConversation(selectedChannelId, { external_user_id: ext })
      const created = res.data
      setNewChatOpen(false)
      setNewChatUserId('')
      const conversationRes = await listOmnichannelConversations(selectedChannelId, { limit: 50 })
      const next = conversationRes.data || []
      setConversations(next)
      if (created?.id)
        setSelectedConversationId(created.id)
      else if (next[0]?.id)
        setSelectedConversationId(next[0].id)
      toast.success(t('settings.omnichannelNewChatCreated'))
    }
    catch {
      toast.error(t('settings.omnichannelNewChatError'))
    }
    finally {
      setIsCreatingChat(false)
    }
  }

  const submitTaskNote = async () => {
    if (!selectedConversationId) {
      toast.error(t('settings.omnichannelTaskNoConversation'))
      return
    }
    const line = taskNote.trim()
    if (!line) {
      toast.error(t('settings.omnichannelTaskEmpty'))
      return
    }
    setIsSavingTask(true)
    try {
      await patchMiniCrmLead(selectedConversationId, { notes_append: line })
      setTaskLogLines(prev => [...prev, { at: new Date().toISOString(), text: line }])
      setTaskModalOpen(false)
      setTaskNote('')
      toast.success(t('settings.omnichannelTaskSaved'))
    }
    catch {
      toast.error(t('settings.omnichannelTaskSaveError'))
    }
    finally {
      setIsSavingTask(false)
    }
  }

  return (
    <>
      <div className="flex h-[calc(100dvh-3.5rem)] min-w-0 flex-1 flex-col overflow-hidden">
        <OmnichannelInboxLayout
          errorBanner={error
            ? (
                <div className="shrink-0 border-b border-state-destructive-border/60 bg-state-destructive-hover-alt px-5 py-2.5 text-sm leading-snug text-text-destructive">
                  {error}
                </div>
              )
            : null}
          inboxSidebar={(
            <OmnichannelInboxSidebar
              channels={channels}
              selectedChannelId={selectedChannelId || ALL_INBOXES_ID}
              onSelectChannel={setSelectedChannelId}
              channelHealthById={channelHealthById}
              unreadByChannelId={unreadByChannelId}
            />
          )}
          conversationRail={(
            <aside className="flex max-h-[42vh] min-h-0 w-full flex-col overflow-hidden border-b border-divider-subtle bg-components-panel-bg xl:max-h-none xl:w-[min(100%,300px)] xl:shrink-0 xl:border-r xl:border-b-0 xl:border-divider-subtle">
              {isInboxBootstrapLoading
                ? <OmnichannelSectionLoading />
                : (
                    <>
                      <div className="shrink-0 px-4 pt-4 pb-3">
                        <div className="relative min-w-0">
                          <RiSearchLine className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-text-quaternary" aria-hidden />
                          <input
                            type="search"
                            value={conversationSearchQuery}
                            onChange={e => setConversationSearchQuery(e.target.value)}
                            placeholder={t('settings.omnichannelSearchChatsPlaceholder')}
                            className="h-10 w-full rounded-lg border-0 bg-background-default py-2 pr-3 pl-10 system-sm-regular text-text-primary shadow-sm ring-1 ring-divider-subtle outline-none ring-inset placeholder:text-text-quaternary focus:ring-2 focus:ring-state-accent-solid"
                          />
                        </div>
                      </div>
                      <div className="min-w-0 shrink-0 px-4 pb-3">
                        <div className="overflow-x-auto overscroll-x-contain [-webkit-overflow-scrolling:touch] [scrollbar-width:thin]">
                          <div
                            className="flex w-max min-w-full gap-1 rounded-lg bg-background-default p-1 ring-1 ring-divider-subtle"
                            role="tablist"
                          >
                            {OMNICHANNEL_TAB_DEFS.map((def) => {
                              const n = def.countKey ? tabCounts[def.countKey] : 0
                              const active = conversationTab === def.id
                              return (
                                <button
                                  key={def.id}
                                  type="button"
                                  className={cn(
                                    'relative min-h-8 shrink-0 rounded-md px-2.5 py-1.5 text-xs font-medium whitespace-nowrap transition-colors sm:px-3',
                                    active
                                      ? 'bg-components-panel-bg text-text-primary shadow-sm'
                                      : 'text-text-tertiary hover:bg-state-base-hover hover:text-text-secondary',
                                  )}
                                  onClick={() => setConversationTab(def.id)}
                                  role="tab"
                                  aria-selected={active}
                                >
                                  <span>{t(def.labelKey as never)}</span>
                                  {def.id === 'open' && n > 0 && (
                                    <span className="ml-1 text-[11px] font-semibold text-text-accent tabular-nums">
                                      (
                                      {n}
                                      )
                                    </span>
                                  )}
                                </button>
                              )
                            })}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1 px-4 pb-2">
                        {(['all', 'mine', 'unassigned'] as const).map((filter) => {
                          const active = assigneeFilter === filter
                          const labelKey = filter === 'all'
                            ? 'settings.omnichannelAssigneeAll'
                            : filter === 'mine'
                              ? 'settings.omnichannelAssigneeMine'
                              : 'settings.omnichannelAssigneeUnassigned'
                          return (
                            <button
                              key={filter}
                              type="button"
                              className={cn(
                                'rounded-md px-2 py-1 text-[11px] font-medium',
                                active ? 'bg-state-base-hover text-text-primary' : 'text-text-tertiary hover:text-text-secondary',
                              )}
                              onClick={() => setAssigneeFilter(filter)}
                            >
                              {t(labelKey as never)}
                            </button>
                          )
                        })}
                      </div>
                      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto px-3 pt-1 pb-4">
                        {!filteredConversations.length && (
                          <div className="px-2 py-6 text-sm text-text-tertiary">{t('settings.omnichannelNoConversations')}</div>
                        )}
                        {filteredConversations.map((item) => {
                          const rowSnippet = (selectedConversationId === item.id && lastMessagePreview)
                            || formatOmnichannelListSnippet(item.last_message_preview)
                          return (
                            <button
                              key={item.id}
                              type="button"
                              className={cn(
                                'flex w-full gap-3 rounded-lg px-3 py-3 text-left transition-colors',
                                selectedConversationId === item.id
                                  ? 'bg-state-base-hover'
                                  : 'hover:bg-state-base-hover/80',
                              )}
                              onClick={() => setSelectedConversationId(item.id)}
                            >
                              <div className="relative shrink-0">
                                <OmnichannelAvatar
                                  size={40}
                                  imageUrl={item.participant_profile_pic_url}
                                  initials={omnichannelInitialsSeed(
                                    (item.participant_display_name && item.participant_display_name.trim()) || item.external_user_id,
                                  )}
                                />
                                <div className="absolute -right-0.5 -bottom-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-components-panel-bg p-0.5 shadow-sm ring-1 ring-divider-subtle">
                                  <ProviderLogo provider={item.channel_type || 'facebook_messenger'} className="size-3.5 rounded-sm" />
                                </div>
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-start justify-between gap-2">
                                  <div className="truncate system-sm-medium text-text-primary">
                                    {(item.participant_display_name && item.participant_display_name.trim()) || item.external_user_id}
                                  </div>
                                  <span className="shrink-0 text-xs whitespace-nowrap text-text-quaternary tabular-nums">
                                    {formatListTime(item.last_message_at)}
                                  </span>
                                  {(item.unread_count || 0) > 0 && (
                                    <span className="rounded-full bg-text-accent px-1.5 py-0.5 text-[10px] font-semibold text-text-primary-on-surface tabular-nums">
                                      {item.unread_count}
                                    </span>
                                  )}
                                </div>
                                <div className="mt-1 line-clamp-2 text-xs leading-relaxed text-text-tertiary">
                                  {rowSnippet || t('settings.omnichannelListSnippetFallback')}
                                </div>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    </>
                  )}
            </aside>
          )}
          conversationMain={(
            <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-background-default xl:border-t-0">
              {isInboxBootstrapLoading
                ? <OmnichannelSectionLoading />
                : (
                    <>
                      {selectedConversation && (
                        <div className="flex shrink-0 flex-wrap items-start justify-between gap-4 border-b border-divider-subtle px-5 py-4 md:px-6">
                          <div className="flex min-w-0 items-start gap-3">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="truncate text-base font-semibold tracking-tight text-text-primary md:text-lg">
                                  {(selectedConversation.participant_display_name && selectedConversation.participant_display_name.trim()) || selectedConversation.external_user_id}
                                </span>
                              </div>
                              <div className="mt-1 truncate text-sm text-text-tertiary">
                                {lastMessagePreview
                                  || formatOmnichannelListSnippet(selectedConversation.last_message_preview)
                                  || t('settings.omnichannelConversationWith', {
                                    id: (selectedConversation.participant_display_name && String(selectedConversation.participant_display_name).trim())
                                      || selectedConversation.external_user_id,
                                  })}
                              </div>
                            </div>
                          </div>
                          <div className="flex shrink-0 flex-wrap items-center gap-2">
                            <div className="flex min-w-[12rem] flex-col gap-1">
                              <span className="text-[11px] font-medium text-text-quaternary uppercase">{t('miniCrm.colOwner')}</span>
                              <MemberSelector
                                value={selectedConversation.assignee_account_id ?? undefined}
                                onSelect={(accountId: string) => { void onAssignConversation(accountId) }}
                              />
                              {selectedConversation.assignee_account_id && (
                                <button
                                  type="button"
                                  className="text-left text-xs text-text-accent hover:opacity-80"
                                  onClick={() => { void onAssignConversation(null) }}
                                >
                                  {t('miniCrm.ownerClear')}
                                </button>
                              )}
                            </div>
                            <span className="rounded-md bg-state-base-hover px-2.5 py-1 text-xs font-medium text-text-secondary">
                              {t('settings.omnichannelConversationStatus')}
                              :
                              {' '}
                              {t(conversationStatusLabelKey(selectedConversation.status) as never)}
                            </span>
                            {(selectedConversation.status || 'open') === 'resolved'
                              ? (
                                  <Button type="button" size="small" variant="secondary" onClick={() => void onReopenConversation()}>
                                    {t('settings.omnichannelReopen')}
                                  </Button>
                                )
                              : (
                                  <Button type="button" size="small" variant="secondary" onClick={() => void onResolveConversation()}>
                                    {t('settings.omnichannelResolve')}
                                  </Button>
                                )}
                          </div>
                        </div>
                      )}
                      <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-4 py-4 md:px-6 md:py-5">

                        {!!selectedConversationId && messagesHasMore && !isMessagesLoading && (
                          <div className="mb-2 text-[11px] leading-snug text-text-quaternary">
                            {t('settings.omnichannelLoadOlderHint')}
                          </div>
                        )}
                        {!selectedConversationId && (
                          <div className="flex flex-1 flex-col items-center justify-center px-4 py-16 text-center">
                            <p className="max-w-sm text-sm leading-relaxed text-text-tertiary">{t('settings.omnichannelSelectConversationHint')}</p>
                          </div>
                        )}
                        {selectedConversationId && (
                          <div className="flex min-h-0 flex-1 flex-col gap-4">
                            {!isMessagesLoading && !!messages.length && (
                              <input
                                type="search"
                                value={messageSearchQuery}
                                onChange={e => setMessageSearchQuery(e.target.value)}
                                placeholder={t('settings.omnichannelSearchMessagesPlaceholder')}
                                className="h-10 w-full max-w-md shrink-0 rounded-lg border-0 bg-components-input-bg-normal px-3 py-2 system-sm-regular text-text-primary shadow-sm ring-1 ring-divider-subtle outline-none ring-inset placeholder:text-text-quaternary focus:ring-2 focus:ring-state-accent-solid"
                              />
                            )}
                            <div className="relative flex min-h-0 flex-1 flex-col">
                              {showJumpToLatest && (
                                <Button
                                  type="button"
                                  className="absolute right-2 bottom-3 z-10 shadow-md"
                                  size="small"
                                  variant="primary"
                                  onClick={() => scrollMessagesToBottom(true)}
                                >
                                  {t('settings.omnichannelJumpToLatest')}
                                </Button>
                              )}
                              <div
                                key={selectedConversationId}
                                ref={messagesScrollRef}
                                onScroll={onMessagesScroll}
                                className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-y-contain px-1 py-2 md:px-2"
                              >
                                {isMessagesLoading && (
                                  <div className="flex min-h-[12rem] items-center justify-center py-8">
                                    <Loading type="area" />
                                  </div>
                                )}
                                {!isMessagesLoading && !messages.length && (
                                  <div className="py-8 text-sm text-text-tertiary">{t('settings.omnichannelNoMessages')}</div>
                                )}
                                {!isMessagesLoading && !!messages.length && (
                                  <>
                                    {isLoadingOlderMessages && (
                                      <div className="mb-2 flex justify-center">
                                        <div className="rounded-full bg-background-default px-3 py-1 text-[11px] text-text-tertiary shadow-sm">
                                          {t('settings.omnichannelLoadingOlderMessages')}
                                        </div>
                                      </div>
                                    )}
                                    {!messagesHasMore && (
                                      <div className="mb-2 text-center text-[10px] text-text-quaternary">
                                        {t('settings.omnichannelHistoryStart')}
                                      </div>
                                    )}
                                    {messageTimelineItems.length === 0 && (
                                      <div className="py-6 text-center text-sm text-text-tertiary">
                                        {t('settings.omnichannelSearchNoResults')}
                                      </div>
                                    )}
                                    {messageTimelineItems.map((item) => {
                                  if (item.kind === 'divider') {
                                    return (
                                      <div key={item.key} className="flex items-center gap-3 py-1">
                                        <div className="h-px flex-1 bg-divider-regular" />
                                        <span className="shrink-0 text-[10px] font-medium tracking-wide text-text-quaternary uppercase">{item.label}</span>
                                        <div className="h-px flex-1 bg-divider-regular" />
                                      </div>
                                    )
                                  }
                                  const message = item.message
                                  const isInternalNote = message.source === 'internal_note'
                                  const isSystemNote = !!message.system_note || !!(message.metadata as { system_note?: boolean })?.system_note
                                  const isOutbound = message.direction === 'outbound' && !isInternalNote
                                  const quotePreview = message.quote_preview
                                    || (message.metadata as { quote_preview?: { content?: string } })?.quote_preview
                                  const inboundSender = (
                                    (message.sender_display_name && String(message.sender_display_name).trim())
                                    || (selectedConversation?.participant_display_name && String(selectedConversation.participant_display_name).trim())
                                    || message.external_user_id
                                  )
                                  const inboundAvatar = message.sender_profile_pic_url || selectedConversation?.participant_profile_pic_url
                                  const outboundSender = (
                                    (message.channel_actor_name && String(message.channel_actor_name).trim())
                                    || (selectedChannel?.name && String(selectedChannel.name).trim())
                                    || t('settings.omnichannelReplyActorFallback')
                                  )
                                  const outboundAvatar = message.channel_actor_picture_url
                                  const actorLabel = isOutbound ? outboundSender : inboundSender
                                  const inboundInitialsSeed = omnichannelInitialsSeed(inboundSender)
                                  const outboundInitialsSeed = omnichannelInitialsSeed(outboundSender)

                                  if (isSystemNote) {
                                    return (
                                      <div key={item.key} className="flex justify-center px-2 py-1">
                                        <div className="max-w-[min(92%,640px)] rounded-lg bg-state-warning-hover-alt px-3 py-2 text-center text-xs leading-relaxed text-text-secondary ring-1 ring-divider-subtle">
                                          {message.content}
                                        </div>
                                      </div>
                                    )
                                  }

                                  if (isInternalNote) {
                                    return (
                                      <div key={item.key} className="flex justify-center px-2 py-1">
                                        <div className="max-w-[min(92%,640px)] rounded-lg border border-dashed border-divider-subtle bg-state-base-hover px-3 py-2 text-xs leading-relaxed text-text-secondary">
                                          <div className="mb-1 font-medium text-text-primary">{t('settings.omnichannelInternalNoteLabel')}</div>
                                          {message.content}
                                        </div>
                                      </div>
                                    )
                                  }

                                  return (
                                    <div
                                      key={item.key}
                                      className={`group flex items-end gap-2 ${isOutbound ? 'justify-end' : 'justify-start'}`}
                                    >
                                      {!isOutbound && (
                                        <OmnichannelAvatar imageUrl={inboundAvatar} initials={inboundInitialsSeed} size={36} />
                                      )}
                                      <div className="flex max-w-[min(88%,560px)] flex-col gap-1">
                                        <div
                                          className={cn(
                                            'rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed shadow-sm',
                                            isOutbound
                                              ? 'bg-text-accent text-text-primary-on-surface'
                                              : 'bg-components-panel-bg text-text-primary ring-1 ring-divider-subtle',
                                          )}
                                        >
                                          <div className="mb-1 space-y-0.5">
                                            <div className={cn('text-xs font-medium', isOutbound ? 'text-text-primary-on-surface/90' : 'text-text-secondary')}>{actorLabel}</div>
                                            <div className={cn('flex flex-wrap items-center justify-between gap-x-2 text-[10px]', isOutbound ? 'text-text-primary-on-surface/75' : 'text-text-tertiary')}>
                                              <span>{messageDirectionAndSource(message.direction, message.source, message.metadata)}</span>
                                              <span className="shrink-0 tabular-nums">{toLocaleText(message.created_at)}</span>
                                            </div>
                                          </div>
                                          {!!quotePreview?.content && (
                                            <div className={cn(
                                              'mb-2 rounded-lg border-l-2 px-2 py-1 text-xs opacity-90',
                                              isOutbound ? 'border-text-primary-on-surface/60 bg-black/10' : 'border-text-accent bg-state-base-hover',
                                            )}
                                            >
                                              <div className="font-medium">{t('settings.omnichannelQuotedMessage')}</div>
                                              <div className="line-clamp-3">{quotePreview.content}</div>
                                            </div>
                                          )}
                                          <OmnichannelMessageContent
                                            content={message.content || ''}
                                            emptyLabel={t('settings.omnichannelMessageEmpty')}
                                            variant={isOutbound ? 'onAccent' : 'default'}
                                          />
                                          {!!message.attachments?.length && (
                                            <div className="mt-2 grid grid-cols-2 gap-2">
                                              {message.attachments.slice(0, 4).map((attachment, idx) => {
                                                const url = typeof attachment.url === 'string' ? attachment.url : ''
                                                if (url && isImageUrl(url) && shouldAttemptRemoteImage(url)) {
                                                  return (
                                                    <a key={`${message.id}-${idx}`} href={url} target="_blank" rel="noreferrer" className="block">
                                                      <SafeRemoteImage
                                                        src={url}
                                                        alt={t('settings.omnichannelAttachmentAlt')}
                                                        className="h-24 w-full rounded-lg border border-divider-subtle object-cover"
                                                        fallback={(
                                                          <div className="flex h-24 items-center justify-center rounded-lg border border-divider-subtle bg-background-default p-2 text-xs text-text-tertiary">
                                                            {t('settings.omnichannelAttachment')}
                                                          </div>
                                                        )}
                                                      />
                                                    </a>
                                                  )
                                                }
                                                return (
                                                  <div key={`${message.id}-${idx}`} className="rounded-lg border border-divider-subtle bg-background-default p-2 text-xs text-text-tertiary">
                                                    {t('settings.omnichannelAttachment')}
                                                  </div>
                                                )
                                              })}
                                            </div>
                                          )}
                                        </div>
                                        {supportsComposerReplyTo(activeChannelType) && message.direction === 'inbound' && (
                                          <button
                                            type="button"
                                            className="self-end rounded-md px-1 py-0.5 text-[10px] font-medium text-text-tertiary opacity-0 transition-opacity group-hover:opacity-100 hover:text-text-accent"
                                            onClick={() => setReplyToMessage(message)}
                                          >
                                            <RiReplyLine className="mr-0.5 inline h-3 w-3" />
                                            {t('settings.omnichannelReplyToMessage')}
                                          </button>
                                        )}
                                      </div>
                                      {isOutbound && (
                                        <OmnichannelAvatar imageUrl={outboundAvatar} initials={outboundInitialsSeed} size={36} />
                                      )}
                                    </div>
                                  )
                                })}
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                      <OmnichannelComposer
                        channelId={activeMessageChannelId || null}
                        conversationId={selectedConversationId || null}
                        channelType={activeChannelType}
                        disabled={!selectedConversationId}
                        isSending={isSendingMessage}
                        isUploading={isUploadingComposerAttachment}
                        lastInboundAt={lastInboundAt}
                        text={composerText}
                        onTextChange={setComposerText}
                        internalNote={composerInternalNote}
                        onInternalNoteChange={setComposerInternalNote}
                        replyTo={replyToMessage}
                        onReplyToClear={() => setReplyToMessage(null)}
                        attachmentUrl={composerAttachmentUrl}
                        attachmentType={composerAttachmentType}
                        onAttachmentTypeChange={setComposerAttachmentType}
                        attachmentOpen={composerAttachmentOpen}
                        onAttachmentOpenChange={setComposerAttachmentOpen}
                        attachmentName={composerAttachmentName}
                        attachmentUploadProgress={composerAttachmentUploadProgress}
                        attachmentInputRef={composerAttachmentInputRef}
                        onAttachmentFileChange={onComposerAttachmentFileChange}
                        onAttachmentFile={file => void uploadComposerAttachmentFile(file)}
                        onClearAttachment={clearComposerAttachment}
                        supportsAttachments={supportsComposerAttachmentsFlag}
                        supportsRichComposer={supportsRichComposerFlag}
                        richComposerOpen={composerRichOpen}
                        onRichComposerToggle={() => {
                          setComposerRichOpen(open => !open)
                          if (!composerRichOpen)
                            setComposerAttachmentOpen(false)
                        }}
                        cannedResponses={cannedResponses}
                        onCannedResponsesChanged={refreshCannedResponses}
                        canSend={canSendComposer}
                        onSend={() => void onSendComposer()}
                        onConversationUpdated={() => void refreshChannelData({ includeMessages: false })}
                        richComposerPanel={(
                          <OmnichannelRichComposerPanel
                            channelType={activeChannelType}
                            disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
                            onSend={onSendRichComposer}
                          />
                        )}
                      />
                    </>
                  )}
            </section>
          )}
          insightRail={(
            isInboxBootstrapLoading
              ? <OmnichannelSectionLoading />
              : (
                  <div className="flex min-h-0 flex-col gap-8 px-4 py-6">
                    {selectedConversation && (
                      <section>
                        <div className="mb-4 flex items-center justify-between gap-2">
                          <h2 className="text-xs font-semibold tracking-wide text-text-quaternary uppercase">{t('settings.omnichannelProfileTitle')}</h2>
                          <Link
                            href={`/mini-crm/${selectedCrmVertical}/leads?conversation_id=${encodeURIComponent(selectedConversation.id)}&channel_id=${encodeURIComponent(selectedConversation.channel_id)}`}
                            className="text-xs font-medium text-text-accent-secondary hover:opacity-80"
                          >
                            {t('settings.omnichannelViewDetails')}
                          </Link>
                        </div>
                        <div className="flex flex-col items-center text-center">
                          <OmnichannelAvatar
                            size={64}
                            imageUrl={selectedConversation.participant_profile_pic_url}
                            initials={omnichannelInitialsSeed(
                              (selectedConversation.participant_display_name && selectedConversation.participant_display_name.trim()) || selectedConversation.external_user_id,
                            )}
                          />
                          <div className="mt-4 text-sm font-semibold text-text-primary">
                            {(selectedConversation.participant_display_name && selectedConversation.participant_display_name.trim()) || selectedConversation.external_user_id}
                          </div>
                          <div className="mt-1 max-w-full text-xs leading-relaxed text-text-tertiary">
                            {t('settings.omnichannelProfileSubtitle', { channel: channelTypeLabel(selectedConversation.channel_type) })}
                          </div>
                        </div>
                      </section>
                    )}

                    {selectedConversation && selectedConversationId && (
                      <OmnichannelCrmPanel
                        key={`${selectedConversationId}-${crmRefreshKey}`}
                        conversationId={selectedConversationId}
                        channelId={selectedConversation.channel_id}
                        onLeadSaved={(lead) => {
                          setConversations(prev => prev.map(c => (
                            c.id === selectedConversationId
                              ? { ...c, assignee_account_id: lead.owner_account_id ?? null }
                              : c
                          )))
                        }}
                      />
                    )}

                    <section className="border-t border-divider-subtle pt-8">
                      <div className="mb-3 flex items-center justify-between gap-2">
                        <h2 className="text-sm font-semibold text-text-primary">{t('settings.omnichannelTasksTitle')}</h2>
                        <button
                          type="button"
                          className="text-xs font-medium text-text-accent-secondary hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
                          disabled={!selectedConversationId}
                          onClick={() => setTaskModalOpen(true)}
                        >
                          {t('settings.omnichannelTasksAdd')}
                        </button>
                      </div>
                      {!!taskLogLines.length && (
                        <ul className="mb-3 space-y-2 text-xs text-text-secondary">
                          {taskLogLines.map((item, idx) => (
                            <li key={`${item.at}-${idx}`} className="rounded-lg bg-background-default px-3 py-2 ring-1 ring-divider-subtle">
                              <div className="text-[10px] text-text-quaternary tabular-nums">{toLocaleText(item.at)}</div>
                              <div className="mt-1 whitespace-pre-wrap text-text-primary">{item.text}</div>
                            </li>
                          ))}
                        </ul>
                      )}
                      {!taskLogLines.length && (
                        <p className="text-xs leading-relaxed text-text-tertiary">{t('settings.omnichannelTasksEmpty')}</p>
                      )}
                    </section>

                    <details className="group border-t border-divider-subtle pt-8 [&_summary::-webkit-details-marker]:hidden">
                      <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold tracking-wide text-text-quaternary uppercase">
                        <span>{t('settings.omnichannelChannelOperations')}</span>
                        <span className="text-text-quaternary transition-transform group-open:rotate-180">▾</span>
                      </summary>
                      <div className="mt-4 space-y-4">
                        <div className="space-y-2 rounded-lg bg-background-default px-3 py-3 text-xs text-text-secondary ring-1 ring-divider-subtle">
                          <div className="flex items-center justify-between gap-2">
                            <span>{t('settings.omnichannelStatus')}</span>
                            <span className={health?.enabled ? 'font-medium text-text-success' : 'font-medium text-text-warning'}>
                              {health?.enabled ? t('settings.omnichannelStatusEnabled') : t('settings.omnichannelStatusDisabled')}
                            </span>
                          </div>
                          <div className="flex items-center justify-between gap-2">
                            <span>{t('settings.omnichannelLastInbound')}</span>
                            <span className="text-text-primary tabular-nums">{toLocaleText(health?.last_inbound_at)}</span>
                          </div>
                          <div className="flex items-center justify-between gap-2">
                            <span>{t('settings.omnichannelLastOutbound')}</span>
                            <span className="text-text-primary tabular-nums">{toLocaleText(health?.last_outbound_at)}</span>
                          </div>
                        </div>
                        <Button
                          className="w-full rounded-lg"
                          size="small"
                          loading={isTestingWebhook}
                          disabled={isAllInboxes || !selectedChannelId || isTestingWebhook}
                          onClick={() => void onWebhookTest()}
                        >
                          {t('settings.omnichannelTestWebhook')}
                        </Button>
                      </div>
                    </details>

                    {isZaloOaChannel && activeMessageChannelId && (
                      <ZaloFailedBridgeJobsSection key={activeMessageChannelId} channelId={activeMessageChannelId} />
                    )}

                    <section className="border-t border-divider-subtle pt-8">
                      <h2 className="mb-3 text-xs font-semibold tracking-wide text-text-quaternary uppercase">{t('settings.omnichannelSyncHistory')}</h2>
                      <div className="space-y-3">
                        <Input type="datetime-local" value={syncSince} onChange={e => setSyncSince(e.target.value)} disabled={!isMetaHistorySyncSupported} />
                        <Input type="datetime-local" value={syncUntil} onChange={e => setSyncUntil(e.target.value)} disabled={!isMetaHistorySyncSupported} />
                      </div>
                      <p className="mt-3 text-xs leading-relaxed text-text-quaternary">
                        {isMetaHistorySyncSupported
                          ? t('settings.omnichannelSyncNoDatesMessengerHint')
                          : t('settings.omnichannelSyncHistoryNotSupportedHint')}
                      </p>
                      <Button
                        className="mt-4 w-full rounded-lg"
                        size="small"
                        loading={isSyncing}
                        disabled={isAllInboxes || !selectedChannelId || isSyncing || !isMetaHistorySyncSupported}
                        onClick={() => void onStartSync()}
                      >
                        {t('settings.omnichannelStartSync')}
                      </Button>
                      {syncJob && (
                        <div className="mt-4 space-y-2 rounded-lg bg-background-default px-3 py-3 text-xs text-text-secondary ring-1 ring-divider-subtle">
                          <div className="flex items-center justify-between gap-2">
                            <span>{t('settings.omnichannelJobStatus')}</span>
                            <span className="font-medium text-text-primary">{syncJobStatusLabel(syncJob.status)}</span>
                          </div>
                          <div className="flex items-center justify-between gap-2">
                            <span>{t('settings.omnichannelProgress')}</span>
                            <span className="tabular-nums">
                              {Math.round(syncJob.progress)}
                              %
                            </span>
                          </div>
                          <div className="flex items-center justify-between gap-2">
                            <span>{t('settings.omnichannelSyncedMessages')}</span>
                            <span className="tabular-nums">
                              {syncJob.synced_messages}
                              /
                              {syncJob.total_messages}
                            </span>
                          </div>
                        </div>
                      )}
                    </section>

                    <section className="border-t border-divider-subtle pt-8">
                      <h2 className="mb-3 text-xs font-semibold tracking-wide text-text-quaternary uppercase">{t('settings.omnichannelStats')}</h2>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-lg bg-background-default px-3 py-3 ring-1 ring-divider-subtle">
                          <div className="text-xs text-text-tertiary">{t('settings.omnichannelStatTotal')}</div>
                          <div className="mt-1 text-lg font-semibold text-text-primary tabular-nums">{stats?.total_messages ?? 0}</div>
                        </div>
                        <div className="rounded-lg bg-background-default px-3 py-3 ring-1 ring-divider-subtle">
                          <div className="text-xs text-text-tertiary">{t('settings.omnichannelStatConversations')}</div>
                          <div className="mt-1 text-lg font-semibold text-text-primary tabular-nums">{stats?.active_conversations ?? 0}</div>
                        </div>
                        <div className="rounded-lg bg-background-default px-3 py-3 ring-1 ring-divider-subtle">
                          <div className="text-xs text-text-tertiary">{t('settings.omnichannelStatInbound')}</div>
                          <div className="mt-1 text-lg font-semibold text-text-primary tabular-nums">{stats?.inbound_messages ?? 0}</div>
                        </div>
                        <div className="rounded-lg bg-background-default px-3 py-3 ring-1 ring-divider-subtle">
                          <div className="text-xs text-text-tertiary">{t('settings.omnichannelStatOutbound')}</div>
                          <div className="mt-1 text-lg font-semibold text-text-primary tabular-nums">{stats?.outbound_messages ?? 0}</div>
                        </div>
                      </div>
                    </section>

                    <section className="border-t border-divider-subtle pt-8 pb-2">
                      <h2 className="mb-3 text-sm font-semibold text-text-primary">{t('settings.omnichannelMediaPreview')}</h2>
                      {!imageAttachments.length && (
                        <div className="rounded-lg bg-background-default px-3 py-4 text-xs text-text-tertiary ring-1 ring-divider-subtle">
                          {t('settings.omnichannelMediaPreviewEmpty')}
                        </div>
                      )}
                      {!!imageAttachments.length && (
                        <div className="grid grid-cols-3 gap-2">
                          {imageAttachments.map(item => (
                            <a key={`${item.id}-${item.url}`} href={item.url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-md ring-1 ring-divider-subtle">
                              <SafeRemoteImage
                                src={item.url}
                                alt={t('settings.omnichannelMediaAlt')}
                                className="h-16 w-full object-cover"
                                fallback={(
                                  <div className="flex h-16 items-center justify-center bg-background-default text-[10px] text-text-tertiary">
                                    —
                                  </div>
                                )}
                              />
                            </a>
                          ))}
                        </div>
                      )}
                    </section>
                  </div>
                )
          )}
        />
      </div>
      <Modal
        isShow={newChatOpen}
        onClose={() => {
          setNewChatOpen(false)
          setNewChatUserId('')
        }}
        title={t('settings.omnichannelNewChatModalTitle')}
        description={t('settings.omnichannelNewChatModalDescription')}
        closable
        highPriority
      >
        <div className="mt-4 space-y-4">
          <Input
            value={newChatUserId}
            onChange={e => setNewChatUserId(e.target.value)}
            placeholder={t('settings.omnichannelNewChatUserIdPlaceholder')}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              size="small"
              variant="secondary"
              onClick={() => {
                setNewChatOpen(false)
                setNewChatUserId('')
              }}
            >
              {t('operation.cancel')}
            </Button>
            <Button
              type="button"
              size="small"
              variant="primary"
              loading={isCreatingChat}
              onClick={() => void submitNewChat()}
            >
              {t('settings.omnichannelNewChatConfirm')}
            </Button>
          </div>
        </div>
      </Modal>
      <Modal
        isShow={taskModalOpen}
        onClose={() => {
          setTaskModalOpen(false)
          setTaskNote('')
        }}
        title={t('settings.omnichannelTaskModalTitle')}
        description={t('settings.omnichannelTaskModalDescription')}
        closable
        highPriority
      >
        <div className="mt-4 space-y-4">
          <textarea
            rows={4}
            value={taskNote}
            onChange={e => setTaskNote(e.target.value)}
            className="w-full resize-none rounded-xl border-0 bg-components-input-bg-normal px-3 py-2 system-sm-regular text-text-primary shadow-sm ring-1 ring-divider-subtle outline-none ring-inset"
            placeholder={t('settings.omnichannelTaskModalPlaceholder')}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              size="small"
              variant="secondary"
              onClick={() => {
                setTaskModalOpen(false)
                setTaskNote('')
              }}
            >
              {t('operation.cancel')}
            </Button>
            <Button
              type="button"
              size="small"
              variant="primary"
              loading={isSavingTask}
              onClick={() => void submitTaskNote()}
            >
              {t('settings.omnichannelTaskModalSave')}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}

const OmnichannelPage = () => (
  <Suspense
    fallback={(
      <div className="flex min-h-[50vh] flex-1 items-center justify-center">
        <Loading type="app" />
      </div>
    )}
  >
    <OmnichannelPageContent />
  </Suspense>
)

export default OmnichannelPage
