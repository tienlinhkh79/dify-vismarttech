'use client'

import type { Channel } from '@/service/tools'
import { useTranslation } from '#i18n'
import { ProviderLogo } from '@/app/components/header/account-setting/channels-ui'
import { cn } from '@/utils/classnames'

export const ALL_INBOXES_ID = '__all__'

type ChannelHealthMap = Record<string, { enabled: boolean, last_inbound_at?: string } | undefined>

type OmnichannelInboxSidebarProps = {
  channels: Channel[]
  selectedChannelId: string
  onSelectChannel: (channelId: string) => void
  channelHealthById?: ChannelHealthMap
  unreadByChannelId?: Record<string, number>
}

function connectionBadge(status?: string, enabled?: boolean) {
  if (enabled === false)
    return 'bg-text-quaternary'
  if (status === 'connected')
    return 'bg-text-success'
  if (status === 'pending_auth' || status === 'pending_qr')
    return 'bg-text-warning'
  if (status === 'expired' || status === 'worker_unreachable' || status === 'worker_unconfigured')
    return 'bg-text-destructive'
  return 'bg-text-quaternary'
}

export function OmnichannelInboxSidebar({
  channels,
  selectedChannelId,
  onSelectChannel,
  channelHealthById = {},
  unreadByChannelId = {},
}: OmnichannelInboxSidebarProps) {
  const { t } = useTranslation('common')

  const allUnread = Object.values(unreadByChannelId).reduce((sum, n) => sum + (n || 0), 0)

  return (
    <aside className="hidden min-h-0 w-[min(100%,220px)] shrink-0 flex-col overflow-hidden border-r border-divider-subtle bg-components-panel-bg xl:flex">
      <div className="shrink-0 border-b border-divider-subtle px-3 py-3">
        <div className="text-xs font-semibold tracking-wide text-text-tertiary uppercase">
          {t('settings.omnichannelInboxesSidebarTitle')}
        </div>
      </div>
      <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto p-2">
        <button
          type="button"
          className={cn(
            'flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left transition-colors',
            selectedChannelId === ALL_INBOXES_ID
              ? 'bg-state-base-hover text-text-primary'
              : 'text-text-secondary hover:bg-state-base-hover/80',
          )}
          onClick={() => onSelectChannel(ALL_INBOXES_ID)}
        >
          <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-background-default text-[10px] font-bold text-text-tertiary ring-1 ring-divider-subtle">
            ALL
          </span>
          <span className="min-w-0 flex-1 truncate system-sm-medium">{t('settings.omnichannelAllInboxes')}</span>
          {allUnread > 0 && (
            <span className="rounded-full bg-text-accent px-1.5 py-0.5 text-[10px] font-semibold text-text-primary-on-surface tabular-nums">
              {allUnread > 99 ? '99+' : allUnread}
            </span>
          )}
        </button>
        {channels.map((channel) => {
          const health = channelHealthById[channel.channel_id]
          const oauthStatus = (channel as Channel & { oauth_status?: string, personal_login_status?: string }).oauth_status
            || (channel as Channel & { personal_login_status?: string }).personal_login_status
          const unread = unreadByChannelId[channel.channel_id] || 0
          const active = selectedChannelId === channel.channel_id
          return (
            <button
              key={channel.channel_id}
              type="button"
              className={cn(
                'flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left transition-colors',
                active
                  ? 'bg-state-base-hover text-text-primary'
                  : 'text-text-secondary hover:bg-state-base-hover/80',
              )}
              onClick={() => onSelectChannel(channel.channel_id)}
            >
              <span className="relative shrink-0">
                <ProviderLogo provider={channel.channel_type} className="size-7 rounded-md" />
                <span
                  className={cn(
                    'absolute -right-0.5 -bottom-0.5 size-2 rounded-full ring-2 ring-components-panel-bg',
                    connectionBadge(oauthStatus, health?.enabled ?? channel.enabled),
                  )}
                  title={t('settings.omnichannelInboxConnectionStatus')}
                />
              </span>
              <span className="min-w-0 flex-1 truncate system-sm-medium">{channel.name}</span>
              {unread > 0 && (
                <span className="rounded-full bg-text-accent px-1.5 py-0.5 text-[10px] font-semibold text-text-primary-on-surface tabular-nums">
                  {unread > 99 ? '99+' : unread}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </aside>
  )
}
