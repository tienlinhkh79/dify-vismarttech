'use client'

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from '#i18n'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { ProviderLogo } from '@/app/components/header/account-setting/channels-ui'
import {
  getOmnichannelHealth,
  getOmnichannelStats,
  getOmnichannelSyncJob,
  listChannels,
  listOmnichannelConversations,
  listOmnichannelMessages,
  refreshOmnichannelConversationParticipant,
  startOmnichannelHistorySync,
  testOmnichannelWebhook,
  type Channel,
  type OmnichannelConversation,
  type OmnichannelMessage,
  type OmnichannelSyncJob,
} from '@/service/tools'
import { API_PREFIX } from '@/config'
import { getBaseURL } from '@/service/client'

function omnichannelSseUrl(channelId: string): string {
  const segment = `workspaces/current/channels/${encodeURIComponent(channelId)}/stream`
  const base = getBaseURL(API_PREFIX)
  const root = base.href.replace(/\/?$/, '')
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

const terminalSyncStatuses = new Set(['succeeded', 'failed'])

const getChannelGradient = (channelType?: string) => {
  if (channelType?.includes('instagram'))
    return 'from-purple-500/20 via-pink-500/20 to-orange-400/20'
  if (channelType?.includes('zalo'))
    return 'from-blue-500/20 via-cyan-400/20 to-sky-300/20'
  return 'from-blue-500/20 via-indigo-500/20 to-violet-500/20'
}

const isImageUrl = (url: string) => /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(url)

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
  const [imageFailed, setImageFailed] = useState(false)
  useEffect(() => {
    setImageFailed(false)
  }, [imageUrl])
  const label = (initials || '?').slice(0, 2).toUpperCase()
  const trimmedUrl = (imageUrl || '').trim()
  const showImage = Boolean(trimmedUrl) && !imageFailed
  return (
    <div
      className='shrink-0 overflow-hidden rounded-full border border-divider-subtle bg-background-default shadow-sm'
      style={{ width: size, height: size }}
    >
      {showImage
        ? (
            <img
              src={trimmedUrl}
              alt=''
              className='size-full object-cover'
              onError={() => setImageFailed(true)}
            />
          )
        : (
            <div className='flex size-full items-center justify-center text-[10px] font-semibold text-text-tertiary'>
              {label}
            </div>
          )}
    </div>
  )
}

/** Newest-first pages from API; we render chronological ascending (oldest → newest).
 *  Fallback poll when SSE is unavailable; primary updates use Redis → SSE.
 */
const OMNICHANNEL_FALLBACK_POLL_MS = 45_000
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

const OmnichannelPage = () => {
  const { t, i18n } = useTranslation('common')
  const dateLocale = i18n.language?.replace('_', '-') || undefined
  const toLocaleText = (value?: string) => {
    if (!value)
      return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime()))
      return value
    return date.toLocaleString(dateLocale)
  }
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
  const [isMessagesLoading, setIsMessagesLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isTestingWebhook, setIsTestingWebhook] = useState(false)
  const [error, setError] = useState('')
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
  const messengerParticipantRefreshAttemptedRef = useRef('')
  const selectedChannelIdRef = useRef('')
  const selectedConversationIdRef = useRef('')
  const isMessagesLoadingRef = useRef(false)
  const isLoadingOlderMessagesRef = useRef(false)
  const omnichannelRealtimeDebounceRef = useRef<number | null>(null)

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
    messengerParticipantRefreshAttemptedRef.current = ''
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
    (async () => {
      const response = await listChannels()
      const nextChannels = response.data || []
      setChannels(nextChannels)
      if (nextChannels.length > 0)
        setSelectedChannelId(nextChannels[0].channel_id)
    })().catch(() => {
      setError(t('settings.omnichannelErrorLoadChannels'))
    })
  }, [t, i18n.language])

  useEffect(() => {
    if (!selectedChannelId)
      return

    setIsPageLoading(true)
    setError('')
    ;(async () => {
      try {
        const [conversationRes, statsRes, healthRes] = await Promise.all([
          listOmnichannelConversations(selectedChannelId, { limit: 50 }),
          getOmnichannelStats(selectedChannelId),
          getOmnichannelHealth(selectedChannelId),
        ])
        const nextConversations = conversationRes.data || []
        setConversations(nextConversations)
        setSelectedConversationId((prev) => {
          if (prev && nextConversations.some(item => item.id === prev))
            return prev
          return nextConversations[0]?.id || ''
        })
        setStats(statsRes.data)
        setHealth(healthRes.data)
      }
      catch {
        setError(t('settings.omnichannelErrorLoadData'))
      }
      finally {
        setIsPageLoading(false)
      }
    })()
  }, [selectedChannelId, t, i18n.language])

  useEffect(() => {
    if (!selectedChannelId || !selectedConversationId)
      return

    initialScrollToBottomRef.current = true
    allowOlderFromScrollRef.current = false
    setMessageSearchQuery('')
    setMessages([])
    setMessagesHasMore(false)
    messagesPaginationRef.current = { hasMore: false, nextCursor: null }
    setShowJumpToLatest(false)
    setIsMessagesLoading(true)

    listOmnichannelMessages(selectedChannelId, selectedConversationId, { limit: OMNICHANNEL_MESSAGES_PAGE_SIZE })
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
  }, [selectedChannelId, selectedConversationId])

  const loadOlderMessages = useCallback(async () => {
    if (!selectedChannelId || !selectedConversationId)
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
      const res = await listOmnichannelMessages(selectedChannelId, selectedConversationId, {
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
  }, [selectedChannelId, selectedConversationId])

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

    let resolvedConversationId = selectedConversationIdRef.current
    try {
      const [conversationRes, statsRes, healthRes] = await Promise.all([
        listOmnichannelConversations(channelId, { limit: 50 }),
        getOmnichannelStats(channelId),
        getOmnichannelHealth(channelId),
      ])
      const nextConversations = conversationRes.data || []
      const prevSel = selectedConversationIdRef.current
      resolvedConversationId = (prevSel && nextConversations.some(item => item.id === prevSel))
        ? prevSel
        : (nextConversations[0]?.id || '')
      setConversations(nextConversations)
      setSelectedConversationId(resolvedConversationId)
      selectedConversationIdRef.current = resolvedConversationId
      setStats(statsRes.data)
      setHealth(healthRes.data)
    }
    catch {
      // avoid flashing the main error banner on transient failures
    }

    if (!opts?.includeMessages)
      return
    const convId = resolvedConversationId
    if (!convId)
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
      const res = await listOmnichannelMessages(channelId, convId, {
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
  }, [scrollMessagesToBottom])

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
    const intervalId = window.setInterval(() => {
      void refreshChannelData({ includeMessages: true })
    }, OMNICHANNEL_FALLBACK_POLL_MS)
    return () => window.clearInterval(intervalId)
  }, [selectedChannelId, refreshChannelData])

  /** Subscribe to server push for this channel (same session cookies as REST). */
  useEffect(() => {
    if (!selectedChannelId)
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
    return key ? t(key) : status
  }

  const messageDirectionAndSource = (direction: string, source: string) => {
    const dir = direction === 'inbound'
      ? t('settings.omnichannelDirectionInbound')
      : t('settings.omnichannelDirectionOutbound')
    const srcMap: Record<string, string> = {
      webhook: 'settings.omnichannelSourceWebhook',
      sync: 'settings.omnichannelSourceSync',
      system: 'settings.omnichannelSourceSystem',
    }
    const srcKey = srcMap[source]
    const src = srcKey ? t(srcKey) : source
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

  type TimelineItem =
    | { kind: 'divider', key: string, label: string }
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

  const channelOptions = useMemo(() => channels.map(channel => ({
    id: channel.channel_id,
    label: `${channel.name} (${channelTypeLabel(channel.channel_type)})`,
  })), [channels, t, i18n.language])

  const selectedChannel = useMemo(
    () => channels.find(item => item.channel_id === selectedChannelId),
    [channels, selectedChannelId],
  )

  const isMetaHistorySyncSupported = useMemo(() => {
    const ct = selectedChannel?.channel_type
    return ct === 'facebook_messenger' || ct === 'instagram_dm'
  }, [selectedChannel?.channel_type])

  const selectedConversation = useMemo(
    () => conversations.find(item => item.id === selectedConversationId),
    [conversations, selectedConversationId],
  )

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
      const payload: { since?: string; until?: string } = {}
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

  return (
    <div className='mx-auto w-full max-w-[1600px] px-6 py-6'>
      <div className={`mb-4 rounded-2xl border border-components-panel-border bg-gradient-to-r ${getChannelGradient(selectedChannel?.channel_type)} p-5`}>
        <div className='flex items-center justify-between gap-4'>
          <div>
            <h2 className='text-xl font-semibold text-text-primary'>{t('settings.omnichannelPageTitle')}</h2>
            <p className='mt-1 text-sm text-text-secondary'>
              {t('settings.omnichannelPageSubtitle')}
            </p>
          </div>
          <div className='hidden items-center gap-3 rounded-xl border border-white/40 bg-white/50 px-3 py-2 backdrop-blur md:flex'>
            <ProviderLogo provider={selectedChannel?.channel_type || 'facebook_messenger'} className='size-8 rounded-lg' />
            <div>
              <div className='text-xs text-text-tertiary'>{t('settings.omnichannelActiveChannel')}</div>
              <div className='text-sm font-medium text-text-primary'>{selectedChannel?.name || t('settings.omnichannelNoChannelSelected')}</div>
            </div>
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)_360px]'>
        <div className='space-y-4'>
          <div className='rounded-xl border border-components-panel-border bg-components-panel-bg p-4'>
            <div className='system-xs-semibold-uppercase mb-2 text-text-tertiary'>{t('settings.omnichannelSectionChannel')}</div>
            <select
              className='h-10 w-full rounded-lg border border-components-input-border bg-components-input-bg px-3 text-sm text-text-primary'
              value={selectedChannelId}
              onChange={e => setSelectedChannelId(e.target.value)}
            >
              {!channelOptions.length && <option value="">{t('settings.omnichannelNoChannelsOption')}</option>}
              {channelOptions.map(option => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </select>
            <div className='mt-3 space-y-2 rounded-lg border border-divider-subtle bg-background-default p-3 text-xs text-text-secondary'>
              <div className='flex items-center justify-between'>
                <span>{t('settings.omnichannelStatus')}</span>
                <span className={health?.enabled ? 'text-green-600' : 'text-yellow-600'}>
                  {health?.enabled ? t('settings.omnichannelStatusEnabled') : t('settings.omnichannelStatusDisabled')}
                </span>
              </div>
              <div className='flex items-center justify-between'>
                <span>{t('settings.omnichannelLastInbound')}</span>
                <span>{toLocaleText(health?.last_inbound_at)}</span>
              </div>
              <div className='flex items-center justify-between'>
                <span>{t('settings.omnichannelLastOutbound')}</span>
                <span>{toLocaleText(health?.last_outbound_at)}</span>
              </div>
            </div>
            <Button
              className='mt-3'
              size='small'
              loading={isTestingWebhook}
              disabled={!selectedChannelId || isTestingWebhook}
              onClick={onWebhookTest}
            >
              {t('settings.omnichannelTestWebhook')}
            </Button>
          </div>

          <div className='rounded-xl border border-components-panel-border bg-components-panel-bg p-4'>
            <div className='mb-2 text-sm font-medium text-text-primary'>{t('settings.omnichannelConversations')}</div>
            {isPageLoading && <div className='text-sm text-text-tertiary'>{t('settings.omnichannelLoadingConversations')}</div>}
            {!isPageLoading && !conversations.length && <div className='text-sm text-text-tertiary'>{t('settings.omnichannelNoConversations')}</div>}
            <div className='max-h-[520px] space-y-2 overflow-auto pr-1'>
              {!isPageLoading && conversations.map(item => (
                <button
                  key={item.id}
                  className={`block w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    selectedConversationId === item.id
                      ? 'border-primary-300 bg-primary-50'
                      : 'border-divider-subtle hover:bg-components-button-secondary-bg'
                  }`}
                  onClick={() => setSelectedConversationId(item.id)}
                >
                  <div className='flex items-start gap-2'>
                    <OmnichannelAvatar
                      size={36}
                      imageUrl={item.participant_profile_pic_url}
                      initials={omnichannelInitialsSeed(
                        (item.participant_display_name && item.participant_display_name.trim()) || item.external_user_id,
                      )}
                    />
                    <div className='min-w-0 flex-1'>
                      <div className='flex items-center justify-between gap-2'>
                        <div className='truncate font-medium text-text-primary'>
                          {(item.participant_display_name && item.participant_display_name.trim()) || item.external_user_id}
                        </div>
                        <span className='shrink-0 text-[10px] uppercase text-text-tertiary'>{channelTypeLabel(item.channel_type)}</span>
                      </div>
                      <div className='truncate text-[11px] text-text-quaternary'>{item.external_user_id}</div>
                      <div className='text-xs text-text-tertiary'>{t('settings.omnichannelLastMessage', { time: toLocaleText(item.last_message_at) })}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className='rounded-xl border border-components-panel-border bg-components-panel-bg p-4'>
          <div className='mb-3 flex flex-wrap items-start justify-between gap-2'>
            <div className='min-w-0 flex-1'>
              <div className='text-sm font-medium text-text-primary'>{t('settings.omnichannelMessages')}</div>
              <div className='text-xs text-text-tertiary'>
                {selectedConversation
                  ? t('settings.omnichannelConversationWith', {
                      id: (selectedConversation.participant_display_name && String(selectedConversation.participant_display_name).trim())
                        || selectedConversation.external_user_id,
                    })
                  : t('settings.omnichannelSelectConversationHint')}
              </div>
              {!!selectedConversationId && messagesHasMore && !isMessagesLoading && (
                <div className='mt-1 text-[11px] leading-snug text-text-quaternary'>
                  {t('settings.omnichannelLoadOlderHint')}
                </div>
              )}
            </div>
            <div className='shrink-0 text-right text-xs text-text-tertiary'>
              {!!selectedConversationId && !isMessagesLoading && (
                <span>{t('settings.omnichannelMessageCount', { count: messages.length })}</span>
              )}
            </div>
          </div>

          {!selectedConversationId && <div className='text-sm text-text-tertiary'>{t('settings.omnichannelSelectConversationHint')}</div>}
          {selectedConversationId && isMessagesLoading && <div className='text-sm text-text-tertiary'>{t('settings.omnichannelLoadingMessages')}</div>}
          {selectedConversationId && !isMessagesLoading && !messages.length && <div className='text-sm text-text-tertiary'>{t('settings.omnichannelNoMessages')}</div>}

          {selectedConversationId && !isMessagesLoading && !!messages.length && (
            <div className='mt-2 space-y-2'>
              <input
                type='search'
                value={messageSearchQuery}
                onChange={e => setMessageSearchQuery(e.target.value)}
                placeholder={t('settings.omnichannelSearchMessagesPlaceholder')}
                className='system-sm-regular w-full rounded-lg border border-divider-regular bg-components-input-bg-normal px-3 py-2 text-text-primary outline-none placeholder:text-text-quaternary focus:border-state-accent-solid'
              />
              <div className='relative min-h-[360px]'>
                {showJumpToLatest && (
                  <Button
                    type='button'
                    className='absolute bottom-3 right-2 z-10 shadow-md'
                    size='small'
                    variant='primary'
                    onClick={() => scrollMessagesToBottom(true)}
                  >
                    {t('settings.omnichannelJumpToLatest')}
                  </Button>
                )}
                <div
                  ref={messagesScrollRef}
                  onScroll={onMessagesScroll}
                  className='max-h-[min(760px,70vh)] min-h-[320px] space-y-3 overflow-y-auto overscroll-y-contain rounded-lg border border-divider-subtle bg-background-default/40 px-2 py-3'
                >
                  {isLoadingOlderMessages && (
                    <div className='mb-2 flex justify-center'>
                      <div className='rounded-full bg-background-default px-3 py-1 text-[11px] text-text-tertiary shadow-sm'>
                        {t('settings.omnichannelLoadingOlderMessages')}
                      </div>
                    </div>
                  )}
                  {!messagesHasMore && (
                    <div className='mb-2 text-center text-[10px] text-text-quaternary'>
                      {t('settings.omnichannelHistoryStart')}
                    </div>
                  )}
                  {messageTimelineItems.length === 0 && (
                    <div className='py-6 text-center text-sm text-text-tertiary'>
                      {t('settings.omnichannelSearchNoResults')}
                    </div>
                  )}
                  {messageTimelineItems.map((item) => {
                    if (item.kind === 'divider') {
                      return (
                        <div key={item.key} className='flex items-center gap-3 py-1'>
                          <div className='h-px flex-1 bg-divider-regular' />
                          <span className='shrink-0 text-[10px] font-medium uppercase tracking-wide text-text-quaternary'>{item.label}</span>
                          <div className='h-px flex-1 bg-divider-regular' />
                        </div>
                      )
                    }
                    const message = item.message
                    const isOutbound = message.direction === 'outbound'
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

                    return (
                      <div
                        key={item.key}
                        className={`flex items-end gap-2 ${isOutbound ? 'justify-end' : 'justify-start'}`}
                      >
                        {!isOutbound && (
                          <OmnichannelAvatar imageUrl={inboundAvatar} initials={inboundInitialsSeed} size={36} />
                        )}
                        <div className={`max-w-[min(85%,520px)] rounded-2xl border px-3 py-2 text-sm shadow-sm ${
                          isOutbound
                            ? 'border-primary-200 bg-primary-50'
                            : 'border-divider-subtle bg-components-panel-bg'
                        }`}
                        >
                          <div className='mb-1 space-y-0.5'>
                            <div className='text-xs font-medium text-text-secondary'>{actorLabel}</div>
                            <div className='flex flex-wrap items-center justify-between gap-x-2 text-[10px] text-text-tertiary'>
                              <span>{messageDirectionAndSource(message.direction, message.source)}</span>
                              <span className='shrink-0 tabular-nums'>{toLocaleText(message.created_at)}</span>
                            </div>
                          </div>
                          <div className='whitespace-pre-wrap break-words text-text-primary'>{message.content || t('settings.omnichannelMessageEmpty')}</div>
                          {!!message.attachments?.length && (
                            <div className='mt-2 grid grid-cols-2 gap-2'>
                              {message.attachments.slice(0, 4).map((attachment, idx) => {
                                const url = typeof attachment.url === 'string' ? attachment.url : ''
                                if (url && isImageUrl(url)) {
                                  return (
                                    <a key={`${message.id}-${idx}`} href={url} target='_blank' rel='noreferrer' className='block'>
                                      <img
                                        src={url}
                                        alt={t('settings.omnichannelAttachmentAlt')}
                                        className='h-24 w-full rounded-lg border border-divider-subtle object-cover'
                                      />
                                    </a>
                                  )
                                }
                                return (
                                  <div key={`${message.id}-${idx}`} className='rounded-lg border border-divider-subtle bg-background-default p-2 text-xs text-text-tertiary'>
                                    {t('settings.omnichannelAttachment')}
                                  </div>
                                )
                              })}
                            </div>
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

        <div className='space-y-4'>
          <div className='rounded-xl border border-components-panel-border bg-components-panel-bg p-4'>
            <div className='system-xs-semibold-uppercase mb-2 text-text-tertiary'>{t('settings.omnichannelSyncHistory')}</div>
            <div className='space-y-2'>
              <Input type='datetime-local' value={syncSince} onChange={e => setSyncSince(e.target.value)} disabled={!isMetaHistorySyncSupported} />
              <Input type='datetime-local' value={syncUntil} onChange={e => setSyncUntil(e.target.value)} disabled={!isMetaHistorySyncSupported} />
            </div>
            <p className='mt-2 text-xs leading-snug text-text-quaternary'>
              {isMetaHistorySyncSupported
                ? t('settings.omnichannelSyncNoDatesMessengerHint')
                : t('settings.omnichannelSyncHistoryNotSupportedHint')}
            </p>
            <Button
              className='mt-3'
              size='small'
              loading={isSyncing}
              disabled={!selectedChannelId || isSyncing || !isMetaHistorySyncSupported}
              onClick={onStartSync}
            >
              {t('settings.omnichannelStartSync')}
            </Button>
            {syncJob && (
              <div className='mt-3 rounded-lg border border-divider-subtle bg-background-default p-3 text-xs text-text-secondary'>
                <div className='flex items-center justify-between'>
                  <span>{t('settings.omnichannelJobStatus')}</span>
                  <span className='font-medium text-text-primary'>{syncJobStatusLabel(syncJob.status)}</span>
                </div>
                <div className='mt-1 flex items-center justify-between'>
                  <span>{t('settings.omnichannelProgress')}</span>
                  <span>{Math.round(syncJob.progress)}%</span>
                </div>
                <div className='mt-1 flex items-center justify-between'>
                  <span>{t('settings.omnichannelSyncedMessages')}</span>
                  <span>{syncJob.synced_messages}/{syncJob.total_messages}</span>
                </div>
              </div>
            )}
          </div>

          <div className='rounded-xl border border-components-panel-border bg-components-panel-bg p-4'>
            <div className='system-xs-semibold-uppercase mb-2 text-text-tertiary'>{t('settings.omnichannelStats')}</div>
            <div className='grid grid-cols-2 gap-2'>
              <div className='rounded-lg border border-divider-subtle bg-background-default p-3'>
                <div className='text-xs text-text-tertiary'>{t('settings.omnichannelStatTotal')}</div>
                <div className='mt-1 text-lg font-semibold'>{stats?.total_messages ?? 0}</div>
              </div>
              <div className='rounded-lg border border-divider-subtle bg-background-default p-3'>
                <div className='text-xs text-text-tertiary'>{t('settings.omnichannelStatConversations')}</div>
                <div className='mt-1 text-lg font-semibold'>{stats?.active_conversations ?? 0}</div>
              </div>
              <div className='rounded-lg border border-divider-subtle bg-background-default p-3'>
                <div className='text-xs text-text-tertiary'>{t('settings.omnichannelStatInbound')}</div>
                <div className='mt-1 text-lg font-semibold'>{stats?.inbound_messages ?? 0}</div>
              </div>
              <div className='rounded-lg border border-divider-subtle bg-background-default p-3'>
                <div className='text-xs text-text-tertiary'>{t('settings.omnichannelStatOutbound')}</div>
                <div className='mt-1 text-lg font-semibold'>{stats?.outbound_messages ?? 0}</div>
              </div>
            </div>
          </div>

          <div className='rounded-xl border border-components-panel-border bg-components-panel-bg p-4'>
            <div className='mb-2 text-sm font-medium text-text-primary'>{t('settings.omnichannelMediaPreview')}</div>
            {!imageAttachments.length && (
              <div className='rounded-lg border border-divider-subtle bg-background-default p-3 text-xs text-text-tertiary'>
                {t('settings.omnichannelMediaPreviewEmpty')}
              </div>
            )}
            {!!imageAttachments.length && (
              <div className='grid grid-cols-3 gap-2'>
                {imageAttachments.map(item => (
                  <a key={`${item.id}-${item.url}`} href={item.url} target='_blank' rel='noreferrer' className='block'>
                    <img src={item.url} alt={t('settings.omnichannelMediaAlt')} className='h-16 w-full rounded-md border border-divider-subtle object-cover' />
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className='mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600'>
          {error}
        </div>
      )}
    </div>
  )
}

export default OmnichannelPage
