'use client'

import type { Channel, OmnichannelConversation, OmnichannelMessage, OmnichannelSyncJob, ZaloBridgeFailedJob } from '@/service/tools'
import { useTranslation } from '#i18n'
import {
  RiAddLine,
  RiAttachmentLine,
  RiDownloadLine,
  RiMore2Fill,
  RiReplyLine,
  RiSearchLine,
  RiSendPlane2Fill,
} from '@remixicon/react'
import { Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import ActionButton from '@/app/components/base/action-button'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Loading from '@/app/components/base/loading'
// eslint-disable-next-line no-restricted-imports -- omnichannel modals; migrate to Dialog in follow-up
import Modal from '@/app/components/base/modal'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/base/ui/dropdown-menu'
import { toast } from '@/app/components/base/ui/toast'
import { ProviderLogo } from '@/app/components/header/account-setting/channels-ui'
import { ACCOUNT_SETTING_TAB } from '@/app/components/header/account-setting/constants'
import MemberSelector from '@/app/components/header/account-setting/members-page/transfer-ownership-modal/member-selector'
import { OmnichannelCrmPanel } from '@/app/components/mini-crm/omnichannel-crm-panel'
import { API_PREFIX } from '@/config'
import { useAppContext } from '@/context/app-context'
import { useAccountSettingModal } from '@/hooks/use-query-params'
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

function OmnichannelAvatar({
  imageUrl,
  initials,
  size = 32,
}: {
  imageUrl?: string | null
  initials: string
  size?: number
}) {
  const [imageFailedForUrl, setImageFailedForUrl] = useState<string | null>(null)
  const label = (initials || '?').slice(0, 2).toUpperCase()
  const trimmedUrl = (imageUrl || '').trim()
  const imageFailed = imageFailedForUrl === trimmedUrl && trimmedUrl !== ''
  const showImage = Boolean(trimmedUrl) && !imageFailed
  return (
    <div
      className="shrink-0 overflow-hidden rounded-full border border-divider-subtle bg-background-default shadow-sm"
      style={{ width: size, height: size }}
    >
      {showImage
        ? (
            <img
              src={trimmedUrl}
              alt=""
              className="size-full object-cover"
              onError={() => setImageFailedForUrl(trimmedUrl)}
            />
          )
        : (
            <div className="flex size-full items-center justify-center text-[10px] font-semibold text-text-tertiary">
              {label}
            </div>
          )}
    </div>
  )
}

/**
 * Newest-first pages from API; we render chronological ascending (oldest → newest).
 *  Fallback poll when SSE is unavailable; primary updates use Redis → SSE.
 */
const OMNICHANNEL_FALLBACK_POLL_MS = 45_000
const OMNICHANNEL_ALL_INBOXES_POLL_MS = 30_000
const OMNICHANNEL_MESSAGES_PAGE_SIZE = 50
const SCROLL_LOAD_OLDER_THRESHOLD_PX = 120
const JUMP_TO_LATEST_DISTANCE_PX = 220

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
  const [, setAccountSettings] = useAccountSettingModal()
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
  const [channelHealthById, setChannelHealthById] = useState<Record<string, ChannelHealth>>({})
  const messengerParticipantRefreshAttemptedRef = useRef('')
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
    if (!selectedChannelId || !selectedConversationId)
      return
    const channel = channels.find(c => c.channel_id === selectedChannelId)
    if (!channel || channel.channel_type !== 'facebook_messenger')
      return
    const conv = conversations.find(c => c.id === selectedConversationId)
    if (!conv)
      return
    const hasName = !!(conv.participant_display_name || '').trim()
    const hasPic = !!(conv.participant_profile_pic_url || '').trim()
    if (hasName && hasPic)
      return
    if (messengerParticipantRefreshAttemptedRef.current === selectedConversationId)
      return
    messengerParticipantRefreshAttemptedRef.current = selectedConversationId

    let cancelled = false
    void (async () => {
      try {
        const res = await refreshOmnichannelConversationParticipant(selectedChannelId, selectedConversationId)
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
  }, [selectedChannelId, selectedConversationId, channels, conversations])

  useEffect(() => {
    queueMicrotask(() => setIsChannelsLoading(true))
    ;(async () => {
      try {
        const response = await listChannels({ include_branding: true })
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
    ;(async () => {
      const entries = await Promise.all(
        channels.map(async (ch) => {
          try {
            const res = await getOmnichannelHealth(ch.channel_id)
            return [ch.channel_id, res.data] as const
          }
          catch {
            return [ch.channel_id, undefined] as const
          }
        }),
      )
      if (!cancelled) {
        const healthMap: Record<string, ChannelHealth> = {}
        for (const [channelId, health] of entries) {
          if (health)
            healthMap[channelId] = health
        }
        setChannelHealthById(healthMap)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [channels])

  useEffect(() => {
    listOmnichannelCannedResponses()
      .then(res => setCannedResponses(res.data || []))
      .catch(() => setCannedResponses([]))
  }, [])

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
    if (!activeMessageChannelId || !selectedConversationId || !isLikelyConversationId(selectedConversationId))
      return
    void markOmnichannelConversationSeen(activeMessageChannelId, selectedConversationId)
      .then((res) => {
        setConversations(prev => prev.map(c => c.id === selectedConversationId ? { ...c, ...res.data, unread_count: 0 } : c))
      })
      .catch(() => {})
  }, [activeMessageChannelId, selectedConversationId])

  useEffect(() => {
    if (!activeMessageChannelId || !selectedConversationId)
      return

    initialScrollToBottomRef.current = true
    allowOlderFromScrollRef.current = false
    queueMicrotask(() => {
      setMessageSearchQuery('')
      setMessages([])
      setMessagesHasMore(false)
      messagesPaginationRef.current = { hasMore: false, nextCursor: null }
      setShowJumpToLatest(false)
      setIsMessagesLoading(true)
    })

    listOmnichannelMessages(activeMessageChannelId, selectedConversationId, { limit: OMNICHANNEL_MESSAGES_PAGE_SIZE })
      .then((res) => {
        const asc = sortMessagesChronological(res.data || [])
        setMessages(asc)
        const hasMore = !!res.has_more
        const nextCur = res.next_cursor ?? null
        setMessagesHasMore(hasMore)
        messagesPaginationRef.current = { hasMore, nextCursor: nextCur }
      })
      .catch(() => {
        setMessages([])
        setMessagesHasMore(false)
        messagesPaginationRef.current = { hasMore: false, nextCursor: null }
      })
      .finally(() => {
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
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const node = messagesScrollRef.current
          if (!node)
            return
          node.scrollTop = node.scrollHeight - prevHeight + prevTop
        })
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
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
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
      void refreshChannelData({ includeMessages: true })
    }, pollMs)
    return () => window.clearInterval(intervalId)
  }, [selectedChannelId, refreshChannelData])

  /** Subscribe to server push for a single channel (same session cookies as REST). */
  useEffect(() => {
    if (!selectedChannelId || selectedChannelId === ALL_INBOXES_ID)
      return
    if (typeof window === 'undefined' || typeof EventSource === 'undefined')
      return

    let es: EventSource | null = null
    let reconnectTimer: number | null = null
    let cancelled = false

    const clearReconnect = () => {
      if (reconnectTimer != null) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    const connect = () => {
      if (cancelled)
        return
      const channelId = selectedChannelIdRef.current
      if (!channelId)
        return
      const url = omnichannelSseUrl(channelId)
      es = new EventSource(url, { withCredentials: true })
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
        es?.close()
        es = null
        if (cancelled)
          return
        clearReconnect()
        reconnectTimer = window.setTimeout(connect, 5000)
      }
    }

    connect()

    return () => {
      cancelled = true
      clearReconnect()
      if (omnichannelRealtimeDebounceRef.current) {
        window.clearTimeout(omnichannelRealtimeDebounceRef.current)
        omnichannelRealtimeDebounceRef.current = null
      }
      es?.close()
    }
  }, [selectedChannelId, scheduleOmnichannelRealtimeRefresh])

  useLayoutEffect(() => {
    if (!initialScrollToBottomRef.current)
      return
    if (isMessagesLoading)
      return
    const el = messagesScrollRef.current
    if (!el || messages.length === 0) {
      initialScrollToBottomRef.current = false
      return
    }
    el.scrollTop = el.scrollHeight
    initialScrollToBottomRef.current = false
    allowOlderFromScrollRef.current = true
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

  const activeChannelType = selectedConversation?.channel_type || selectedChannel?.channel_type
  const isZaloOaChannel = activeChannelType === 'zalo_oa'

  const isInboxBootstrapLoading = isChannelsLoading || (!!selectedChannelId && isPageLoading)

  const supportsComposerAttachments = useMemo(() => {
    const ct = activeChannelType
    return ct === 'facebook_messenger' || ct === 'instagram_dm' || ct === 'zalo_oa'
  }, [activeChannelType])

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
      .filter(item => !!item.url && isImageUrl(item.url))
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

  const downloadConversationTranscript = useCallback(() => {
    if (!selectedConversationId || !selectedChannelId)
      return
    const payload = {
      exported_at: new Date().toISOString(),
      channel_id: selectedChannelId,
      conversation_id: selectedConversationId,
      conversation: selectedConversation,
      messages,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `omnichannel-${selectedChannelId}-${selectedConversationId}.json`
    a.rel = 'noopener'
    a.click()
    URL.revokeObjectURL(url)
    toast.success(t('settings.omnichannelDownloadSuccess'))
  }, [messages, selectedChannelId, selectedConversation, selectedConversationId, t])

  const copyConversationLink = useCallback(async () => {
    if (!selectedChannelId || !selectedConversationId)
      return
    const path = `/omnichannel?channel_id=${encodeURIComponent(selectedChannelId)}&conversation_id=${encodeURIComponent(selectedConversationId)}`
    const absolute = `${window.location.origin}${path}`
    try {
      await navigator.clipboard.writeText(absolute)
      toast.success(t('settings.omnichannelCopyConversationLinkSuccess'))
    }
    catch {
      toast.error(t('settings.omnichannelCopyConversationLinkError'))
    }
  }, [selectedChannelId, selectedConversationId, t])

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
    if (attUrl && !supportsComposerAttachments) {
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
    catch {
      setError(t('settings.omnichannelSendError'))
      toast.error(t('settings.omnichannelSendError'))
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

  const onComposerKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing)
      return
    e.preventDefault()
    if (!selectedConversationId || isSendingMessage || isUploadingComposerAttachment || !canSendComposer)
      return
    void onSendComposer()
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
      <div className="flex min-h-[min(70vh,720px)] min-w-0 flex-1 flex-col overflow-hidden">
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
          toolbar={(
            <div className="flex shrink-0 flex-wrap items-end justify-between gap-x-6 gap-y-4 border-b border-divider-subtle bg-background-default px-5 py-5 md:px-6">
              <div className="min-w-0 space-y-1">
                <h1 className="text-lg font-semibold tracking-tight text-text-primary md:text-xl">{t('settings.omnichannelChatTitle')}</h1>
                <p className="max-w-2xl text-sm leading-relaxed text-text-tertiary">{t('settings.omnichannelPageSubtitle')}</p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center justify-end gap-4">
                <DropdownMenu>
                  <DropdownMenuTrigger
                    type="button"
                    title={t('settings.omnichannelSectionChannel')}
                    disabled={isChannelsLoading}
                    className={cn(
                      'inline-flex h-10 max-w-[min(100vw,300px)] items-center gap-2.5 rounded-lg px-3 py-1.5',
                      'bg-components-input-bg-normal text-text-primary shadow-sm ring-1 ring-divider-subtle ring-inset',
                      'hover:bg-state-base-hover-alt focus:ring-2 focus:ring-state-accent-solid focus:outline-none',
                    )}
                  >
                    <OmnichannelAvatar
                      size={28}
                      imageUrl={selectedChannel?.external_resource_picture_url}
                      initials={omnichannelInitialsSeed(selectedChannel?.name)}
                    />
                    <span className="min-w-0 flex-1 truncate text-left system-sm-regular">
                      {isChannelsLoading
                        ? t('settings.omnichannelLoadingConversations')
                        : selectedChannelId === ALL_INBOXES_ID
                          ? t('settings.omnichannelAllInboxes')
                          : selectedChannel
                            ? `${selectedChannel.name} (${channelTypeLabel(selectedChannel.channel_type)})`
                            : t('settings.omnichannelNoChannelsOption')}
                    </span>
                    {selectedChannel && (
                      <ProviderLogo
                        provider={selectedChannel.channel_type}
                        className="size-5 shrink-0 rounded-sm"
                      />
                    )}
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    placement="bottom-end"
                    sideOffset={8}
                    popupClassName="p-2"
                    className="w-[min(100vw,320px)]"
                  >
                    {!channels.length && (
                      <div className="px-2 py-2.5 text-xs text-text-tertiary">{t('settings.omnichannelNoChannelsOption')}</div>
                    )}
                    <DropdownMenuItem
                      className="h-auto min-h-11 cursor-pointer gap-3 py-2.5"
                      onClick={() => setSelectedChannelId(ALL_INBOXES_ID)}
                    >
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-background-default text-[10px] font-bold text-text-tertiary ring-1 ring-divider-subtle">
                        ALL
                      </div>
                      <div className="min-w-0 flex-1 truncate system-sm-medium text-text-primary">
                        {t('settings.omnichannelAllInboxes')}
                      </div>
                    </DropdownMenuItem>
                    {channels.map(ch => (
                      <DropdownMenuItem
                        key={ch.channel_id}
                        className="h-auto min-h-11 cursor-pointer gap-3 py-2.5"
                        onClick={() => setSelectedChannelId(ch.channel_id)}
                      >
                        <OmnichannelAvatar
                          size={32}
                          imageUrl={ch.external_resource_picture_url}
                          initials={omnichannelInitialsSeed(ch.name)}
                        />
                        <div className="min-w-0 flex-1 space-y-0.5">
                          <div className="truncate system-sm-medium text-text-primary">{ch.name}</div>
                          <div className="truncate text-xs leading-snug text-text-tertiary">{channelTypeLabel(ch.channel_type)}</div>
                        </div>
                        <ProviderLogo provider={ch.channel_type} className="size-5 shrink-0 rounded-sm" />
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button
                  type="button"
                  size="small"
                  variant="secondary"
                  title={t('settings.omnichannelDownloadReportHint')}
                  disabled={!selectedConversationId}
                  onClick={downloadConversationTranscript}
                  className="h-10 min-w-10 px-3"
                >
                  <RiDownloadLine className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  size="small"
                  variant="secondary"
                  title={t('settings.omnichannelStartNewChatHint')}
                  disabled={!activeMessageChannelId || isAllInboxes}
                  onClick={() => setNewChatOpen(true)}
                  className="h-10 gap-1.5 px-3"
                >
                  <RiAddLine className="h-4 w-4" />
                  <span className="hidden sm:inline">{t('settings.omnichannelStartNewChat')}</span>
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger
                    className={cn(
                      'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                      'bg-components-button-secondary-bg text-components-button-secondary-text shadow-sm ring-1 ring-divider-subtle ring-inset',
                      'hover:bg-state-base-hover-alt',
                    )}
                    title={t('settings.omnichannelMoreMenu')}
                  >
                    <RiMore2Fill className="h-4 w-4" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-56">
                    <DropdownMenuItem disabled={isAllInboxes || !selectedChannelId || isTestingWebhook} onClick={() => void onWebhookTest()}>
                      {t('settings.omnichannelTestWebhook')}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      disabled={!selectedChannelId || !selectedConversationId}
                      onClick={() => void copyConversationLink()}
                    >
                      {t('settings.omnichannelCopyConversationLink')}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setAccountSettings({ payload: ACCOUNT_SETTING_TAB.CHANNELS })}
                    >
                      {t('settings.omnichannelManageChannels')}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          )}
          conversationRail={(
            <aside className="flex max-h-[42vh] min-h-0 w-full flex-col overflow-hidden border-b border-divider-subtle bg-components-panel-bg xl:max-h-none xl:w-[min(100%,300px)] xl:shrink-0 xl:border-r xl:border-b-0 xl:border-divider-subtle">
              {isInboxBootstrapLoading
                ? <OmnichannelSectionLoading />
                : (
                    <>
                      <div className="shrink-0 px-4 pt-4 pb-3">
                        <div className="relative">
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
                        {selectedConversationId && isMessagesLoading && <OmnichannelSectionLoading />}
                        {selectedConversationId && !isMessagesLoading && !messages.length && <div className="py-8 text-sm text-text-tertiary">{t('settings.omnichannelNoMessages')}</div>}

                        {selectedConversationId && !isMessagesLoading && !!messages.length && (
                          <div className="flex min-h-0 flex-1 flex-col gap-4">
                            <input
                              type="search"
                              value={messageSearchQuery}
                              onChange={e => setMessageSearchQuery(e.target.value)}
                              placeholder={t('settings.omnichannelSearchMessagesPlaceholder')}
                              className="h-10 w-full max-w-md shrink-0 rounded-lg border-0 bg-components-input-bg-normal px-3 py-2 system-sm-regular text-text-primary shadow-sm ring-1 ring-divider-subtle outline-none ring-inset placeholder:text-text-quaternary focus:ring-2 focus:ring-state-accent-solid"
                            />
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
                                ref={messagesScrollRef}
                                onScroll={onMessagesScroll}
                                className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-y-contain px-1 py-2 md:px-2"
                              >
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
                                          <div className={cn('break-words whitespace-pre-wrap', isOutbound ? 'text-text-primary-on-surface' : 'text-text-primary')}>{message.content || t('settings.omnichannelMessageEmpty')}</div>
                                          {!!message.attachments?.length && (
                                            <div className="mt-2 grid grid-cols-2 gap-2">
                                              {message.attachments.slice(0, 4).map((attachment, idx) => {
                                                const url = typeof attachment.url === 'string' ? attachment.url : ''
                                                if (url && isImageUrl(url)) {
                                                  return (
                                                    <a key={`${message.id}-${idx}`} href={url} target="_blank" rel="noreferrer" className="block">
                                                      <img
                                                        src={url}
                                                        alt={t('settings.omnichannelAttachmentAlt')}
                                                        className="h-24 w-full rounded-lg border border-divider-subtle object-cover"
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
                                        {activeChannelType === 'zalo_oa' && (
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
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="shrink-0 border-t border-divider-subtle bg-background-default px-4 py-3 md:px-6">
                        {replyToMessage && !composerInternalNote && (
                          <div className="mb-2 flex items-start justify-between gap-2 rounded-lg bg-state-base-hover px-3 py-2 text-xs text-text-secondary ring-1 ring-divider-subtle">
                            <div className="min-w-0">
                              <div className="font-medium text-text-primary">{t('settings.omnichannelReplyingTo')}</div>
                              <div className="line-clamp-2">{replyToMessage.content}</div>
                            </div>
                            <button type="button" className="shrink-0 text-text-accent hover:opacity-80" onClick={() => setReplyToMessage(null)}>
                              {t('operation.cancel', { ns: 'common' })}
                            </button>
                          </div>
                        )}
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            className={cn(
                              'rounded-md px-2.5 py-1 text-xs font-medium',
                              composerInternalNote ? 'bg-state-base-hover text-text-primary' : 'text-text-tertiary hover:text-text-secondary',
                            )}
                            onClick={() => setComposerInternalNote(v => !v)}
                          >
                            {t('settings.omnichannelInternalNoteToggle')}
                          </button>
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
                                    onClick={() => setComposerText(item.content)}
                                  >
                                    <span className="system-sm-medium text-text-primary">{item.title}</span>
                                    <span className="line-clamp-2 text-xs text-text-tertiary">{item.content}</span>
                                  </DropdownMenuItem>
                                ))}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          )}
                        </div>
                        <div
                          className={cn(
                            'flex items-end gap-2 rounded-2xl border border-divider-subtle bg-components-input-bg-normal px-3 py-2 shadow-sm ring-1 ring-divider-subtle ring-inset',
                            composerInternalNote && 'border-dashed bg-state-base-hover',
                            (!selectedConversationId || isSendingMessage || isUploadingComposerAttachment) && 'opacity-60',
                          )}
                        >
                          <textarea
                            rows={1}
                            value={composerText}
                            onChange={e => setComposerText(e.target.value)}
                            onKeyDown={onComposerKeyDown}
                            disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
                            className="max-h-[120px] min-h-[36px] flex-1 resize-none bg-transparent py-1.5 system-sm-regular text-text-primary outline-none placeholder:text-text-quaternary disabled:cursor-not-allowed"
                            placeholder={composerInternalNote ? t('settings.omnichannelInternalNotePlaceholder') : t('settings.omnichannelComposerPlaceholder')}
                          />
                          <div className="flex shrink-0 items-center gap-1 pb-0.5">
                            {supportsComposerAttachments && !composerInternalNote && (
                              <ActionButton
                                type="button"
                                size="l"
                                disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
                                aria-label={t('settings.omnichannelComposerAttach')}
                                aria-expanded={composerAttachmentOpen}
                                className={cn(
                                  composerAttachmentOpen && 'action-btn-active',
                                  composerAttachmentUrl.trim() && !composerAttachmentOpen && 'text-text-accent',
                                )}
                                onClick={() => setComposerAttachmentOpen(open => !open)}
                              >
                                <RiAttachmentLine className="h-5 w-5" />
                              </ActionButton>
                            )}
                            <Button
                              type="button"
                              variant="primary"
                              className="h-8 w-8 shrink-0 rounded-lg px-0"
                              loading={isSendingMessage}
                              disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment || !canSendComposer}
                              aria-label={t('settings.omnichannelSend')}
                              onClick={() => void onSendComposer()}
                            >
                              <RiSendPlane2Fill className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        {supportsComposerAttachments && composerAttachmentOpen && (
                          <div className="mt-2 space-y-3 rounded-xl border border-divider-subtle bg-background-default/80 px-3 py-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <input
                                ref={composerAttachmentInputRef}
                                type="file"
                                className="sr-only"
                                disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
                                onChange={e => void onComposerAttachmentFileChange(e)}
                              />
                              <Button
                                type="button"
                                size="small"
                                variant="secondary"
                                loading={isUploadingComposerAttachment}
                                disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
                                onClick={() => composerAttachmentInputRef.current?.click()}
                              >
                                {t('settings.omnichannelComposerUploadFile')}
                              </Button>
                              {!!composerAttachmentName && (
                                <span className="max-w-[min(100%,280px)] truncate text-xs text-text-secondary">
                                  {composerAttachmentName}
                                  {composerAttachmentUploadProgress != null && (
                                    <span className="ml-1 text-text-quaternary tabular-nums">
                                      {composerAttachmentUploadProgress}
                                      %
                                    </span>
                                  )}
                                </span>
                              )}
                              {!!composerAttachmentUrl.trim() && (
                                <button
                                  type="button"
                                  className="text-xs font-medium text-text-accent-secondary hover:opacity-80 disabled:opacity-40"
                                  disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
                                  onClick={clearComposerAttachment}
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
                                  value={composerAttachmentUrl}
                                  readOnly
                                  disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
                                  placeholder={isUploadingComposerAttachment ? t('settings.omnichannelComposerUploading') : 'https://'}
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
                                  value={composerAttachmentType}
                                  onChange={e => setComposerAttachmentType(e.target.value as typeof composerAttachmentType)}
                                  disabled={!selectedConversationId || isSendingMessage || isUploadingComposerAttachment}
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
                      </div>
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
                            href={`/mini-crm?conversation_id=${encodeURIComponent(selectedConversation.id)}&channel_id=${encodeURIComponent(selectedConversation.channel_id)}`}
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
                              <img src={item.url} alt={t('settings.omnichannelMediaAlt')} className="h-16 w-full object-cover" />
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
