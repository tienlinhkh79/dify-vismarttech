'use client'
import type { Channel, ChannelProvider } from '@/service/tools'
import type { ReactNode } from 'react'
import { useId } from 'react'
import Button from '@/app/components/base/button'
import { cn } from '@/utils/classnames'

export type TranslateFn = (key: string, options?: Record<string, unknown>) => string

export type SetupStep = 1 | 2 | 3

/** Brand SVG paths from Simple Icons (CC0): https://github.com/simple-icons/simple-icons */
const SI_MESSENGER_PATH
  = 'M.001 11.639C.001 4.949 5.241 0 12.001 0S24 4.95 24 11.639c0 6.689-5.24 11.638-12 11.638-1.21 0-2.38-.16-3.47-.46a.96.96 0 00-.64.05l-2.39 1.05a.96.96 0 01-1.35-.85l-.07-2.14a.97.97 0 00-.32-.68A11.39 11.389 0 01.002 11.64zm8.32-2.19l-3.52 5.6c-.35.53.32 1.139.82.75l3.79-2.87c.26-.2.6-.2.87 0l2.8 2.1c.84.63 2.04.4 2.6-.48l3.52-5.6c.35-.53-.32-1.13-.82-.75l-3.79 2.87c-.25.2-.6.2-.86 0l-2.8-2.1a1.8 1.8 0 00-2.61.48z'

const SI_FACEBOOK_PATH
  = 'M13.5 24v-10.94h3.7l.55-4.27H13.5V6.06c0-1.24.35-2.08 2.13-2.08h2.27V.16C17.5.11 16.18 0 14.64 0 11.43 0 9.23 1.96 9.23 5.56v3.23H5.5v4.27h3.73V24h4.27z'

const SI_INSTAGRAM_PATH
  = 'M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077'

const SI_TIKTOK_PATH
  = 'M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z'

const SI_ZALO_PATH
  = 'M12.49 10.2722v-.4496h1.3467v6.3218h-.7704a.576.576 0 01-.5763-.5729l-.0006.0005a3.273 3.273 0 01-1.9372.6321c-1.8138 0-3.2844-1.4697-3.2844-3.2823 0-1.8125 1.4706-3.2822 3.2844-3.2822a3.273 3.273 0 011.9372.6321l.0006.0005zM6.9188 7.7896v.205c0 .3823-.051.6944-.2995 1.0605l-.03.0343c-.0542.0615-.1815.206-.2421.2843L2.024 14.8h4.8948v.7682a.5764.5764 0 01-.5767.5761H0v-.3622c0-.4436.1102-.6414.2495-.8476L4.8582 9.23H.1922V7.7896h6.7266zm8.5513 8.3548a.4805.4805 0 01-.4803-.4798v-7.875h1.4416v8.3548H15.47zM20.6934 9.6C22.52 9.6 24 11.0807 24 12.9044c0 1.8252-1.4801 3.306-3.3066 3.306-1.8264 0-3.3066-1.4808-3.3066-3.306 0-1.8237 1.4802-3.3044 3.3066-3.3044zm-10.1412 5.253c1.0675 0 1.9324-.8645 1.9324-1.9312 0-1.065-.865-1.9295-1.9324-1.9295s-1.9324.8644-1.9324 1.9295c0 1.0667.865 1.9312 1.9324 1.9312zm10.1412-.0033c1.0737 0 1.945-.8707 1.945-1.9453 0-1.073-.8713-1.9436-1.945-1.9436-1.0753 0-1.945.8706-1.945 1.9436 0 1.0746.8697 1.9453 1.945 1.9453z'

const brandSvgClass = 'aspect-square h-[72%] w-[72%] max-h-7 shrink-0'

const BrandFacebookIcon = () => (
  <svg viewBox="0 0 24 24" className={cn(brandSvgClass, 'text-white')} xmlns="http://www.w3.org/2000/svg" aria-hidden>
    <path fill="currentColor" d={SI_FACEBOOK_PATH} />
  </svg>
)

const BrandMessengerIcon = () => (
  <svg viewBox="0 0 24 24" className={cn(brandSvgClass, 'text-white')} xmlns="http://www.w3.org/2000/svg" aria-hidden>
    <path fill="currentColor" d={SI_MESSENGER_PATH} />
  </svg>
)

const BrandFacebookMessengerComboIcon = () => (
  <div className="relative h-full w-full">
    <div className="absolute left-0 top-0 flex h-[82%] w-[82%] items-center justify-center rounded-md bg-[#1877F2] p-0.5">
      <BrandFacebookIcon />
    </div>
    <div className="absolute bottom-0 right-0 flex h-[58%] w-[58%] items-center justify-center rounded-md bg-[#00B2FF] p-0.5 ring-1 ring-white">
      <BrandMessengerIcon />
    </div>
  </div>
)

const BrandInstagramIcon = ({ gid }: { gid: string }) => (
  <svg viewBox="0 0 24 24" className={brandSvgClass} xmlns="http://www.w3.org/2000/svg" aria-hidden>
    <defs>
      <linearGradient id={`ig-g-${gid}`} x1="0%" y1="100%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#F58529" />
        <stop offset="45%" stopColor="#DD2A7B" />
        <stop offset="100%" stopColor="#8134AF" />
      </linearGradient>
    </defs>
    <path fill={`url(#ig-g-${gid})`} d={SI_INSTAGRAM_PATH} />
  </svg>
)

const BrandTikTokIcon = () => (
  <svg viewBox="0 0 24 24" className={brandSvgClass} xmlns="http://www.w3.org/2000/svg" aria-hidden>
    <path fill="white" d={SI_TIKTOK_PATH} />
  </svg>
)

const BrandZaloIcon = () => (
  <svg viewBox="0 0 24 24" className={cn(brandSvgClass, 'text-white')} xmlns="http://www.w3.org/2000/svg" aria-hidden>
    <path fill="currentColor" d={SI_ZALO_PATH} />
  </svg>
)

const getProviderLogo = (provider: string, gid: string) => {
  const normalized = provider.toLowerCase()
  if (normalized.includes('zalo')) {
    return {
      icon: <BrandZaloIcon />,
      className: 'bg-[#0068FF]',
    }
  }
  if (normalized.includes('instagram')) {
    return {
      icon: <BrandInstagramIcon gid={gid} />,
      className: 'bg-white',
    }
  }
  if (normalized.includes('tiktok')) {
    return {
      icon: <BrandTikTokIcon />,
      className: 'bg-black',
    }
  }
  if (normalized.includes('messenger') || normalized.includes('facebook')) {
    return {
      icon: <BrandFacebookMessengerComboIcon />,
      className: 'bg-white',
    }
  }
  return {
    icon: 'CH',
    className: 'bg-components-button-secondary-bg text-text-primary',
  }
}

export const ProviderLogo = ({ provider, className = '' }: { provider: string, className?: string }) => {
  const gid = useId().replace(/:/g, '')
  const logo = getProviderLogo(provider, gid)
  return (
    <div className={cn('flex size-6 shrink-0 items-center justify-center rounded-lg p-0.5', logo.className, className)}>
      {typeof logo.icon === 'string' ? <span className="text-[10px] font-semibold">{logo.icon}</span> : logo.icon}
    </div>
  )
}

export const ProviderSummaryCard = ({
  provider,
  configuredCount,
  t,
}: {
  provider: ChannelProvider
  configuredCount: number
  t: TranslateFn
}) => {
  return (
    <div className="rounded-lg border border-divider-subtle px-3 py-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ProviderLogo provider={provider.channel_type} />
          <div className="system-sm-medium text-text-primary">{provider.display_name}</div>
        </div>
        {provider.status === 'coming_soon'
          ? (
            <div className="rounded bg-yellow-100 px-1.5 py-0.5 text-[10px] text-yellow-700">
              {t('settings.channelsComingSoon', { ns: 'common' })}
            </div>
            )
          : (
            <div className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] text-green-700">
              {t('dataSource.website.active', { ns: 'common' })}
            </div>
            )}
      </div>
      <div className="mt-1 system-xs-regular text-text-tertiary">
        {t('settings.channelsConfiguredCount', { ns: 'common', count: configuredCount })}
      </div>
    </div>
  )
}

const getChannelConnectionBadge = (channel: Channel, t: TranslateFn) => {
  if (!channel.enabled)
    return { label: t('dataSource.website.inactive', { ns: 'common' }), className: 'bg-components-button-secondary-bg text-text-tertiary' }
  if (channel.channel_type === 'zalo_oa' && channel.oauth_status === 'pending_auth')
    return { label: t('settings.channelsZaloOAuthPending', { ns: 'common' }), className: 'bg-yellow-100 text-yellow-700' }
  if (channel.channel_type === 'zalo_oa' && channel.oauth_status === 'expired')
    return { label: t('settings.channelsNeedsReauth', { ns: 'common' }), className: 'bg-yellow-100 text-yellow-700' }
  if (channel.status === 'inactive')
    return { label: t('settings.channelsNeedsReauth', { ns: 'common' }), className: 'bg-yellow-100 text-yellow-700' }
  return { label: t('settings.channelsConnected', { ns: 'common' }), className: 'bg-green-100 text-green-700' }
}

export const ChannelItem = ({
  channel,
  t,
  onEdit,
}: {
  channel: Channel
  t: TranslateFn
  onEdit: (channel: Channel) => void
}) => {
  const channelBadge = getChannelConnectionBadge(channel, t)
  return (
    <div className="flex items-center justify-between rounded-lg border border-divider-subtle px-3 py-2">
      <div>
        <div className="flex items-center gap-2">
          <ProviderLogo provider={channel.channel_type} />
          <div className="system-sm-medium text-text-primary">{channel.name || channel.channel_id}</div>
          <div className={`rounded px-1.5 py-0.5 text-[10px] ${channelBadge.className}`}>{channelBadge.label}</div>
        </div>
        <div className="mt-0.5 system-xs-regular text-text-tertiary">
          {channel.platform} · {channel.channel_id} · {channel.enabled ? t('dataSource.website.active', { ns: 'common' }) : t('dataSource.website.inactive', { ns: 'common' })}
        </div>
      </div>
      <Button size="small" variant="secondary" onClick={() => onEdit(channel)}>
        {t('operation.edit', { ns: 'common' })}
      </Button>
    </div>
  )
}

export const SetupProgress = ({ setupStep, t }: { setupStep: SetupStep, t: TranslateFn }) => {
  const steps = [
    t('settings.channelsStepProvider', { ns: 'common' }),
    t('settings.channelsStepAuthorize', { ns: 'common' }),
    t('settings.channelsStepRouting', { ns: 'common' }),
  ]
  return (
    <div className="rounded-lg border border-divider-subtle p-2">
      <div className="mb-2 flex items-center justify-between">
        <div className="system-xs-semibold-uppercase text-text-tertiary">{t('settings.channelsSetupProgress', { ns: 'common' })}</div>
        <div className="system-xs-regular text-text-tertiary">{t('settings.channelsSetupStep', { ns: 'common', step: setupStep, total: 3 })}</div>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {steps.map((item, idx) => {
          const step = (idx + 1) as SetupStep
          const isCompleted = setupStep > step
          const isCurrent = setupStep === step
          return (
            <div
              key={item}
              className={`rounded-md px-2 py-1 text-center text-xs ${isCompleted
                ? 'bg-green-100 text-green-700'
                : isCurrent
                  ? 'bg-primary-50 text-primary-700'
                  : 'bg-components-button-secondary-bg text-text-tertiary'}`}
            >
              {item}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export const SetupProviderSelector = ({
  providers,
  selectedChannelType,
  onSelect,
  t,
}: {
  providers: ChannelProvider[]
  selectedChannelType: string
  onSelect: (provider: ChannelProvider) => void
  t: TranslateFn
}) => (
  <div className="space-y-2">
    <div className="system-xs-semibold-uppercase text-text-tertiary">{t('settings.channelsChooseProvider', { ns: 'common' })}</div>
    <div className="grid grid-cols-1 gap-2">
      {providers.map((provider) => {
        const isSelected = selectedChannelType === provider.channel_type
        const isComingSoon = provider.status === 'coming_soon'
        return (
          <button
            key={provider.channel_type}
            type="button"
            disabled={isComingSoon}
            className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left transition-colors ${isSelected
              ? 'border-primary-300 bg-primary-50'
              : 'border-divider-subtle hover:bg-components-button-secondary-bg'} ${isComingSoon ? 'cursor-not-allowed opacity-70' : ''}`}
            onClick={() => !isComingSoon && onSelect(provider)}
          >
            <div className="flex items-center gap-2">
              <ProviderLogo provider={provider.channel_type} />
              <div className="system-sm-medium text-text-primary">{provider.display_name}</div>
            </div>
            {isComingSoon
              ? (
                <div className="rounded bg-yellow-100 px-1.5 py-0.5 text-[10px] text-yellow-700">
                  {t('settings.channelsComingSoon', { ns: 'common' })}
                </div>
                )
              : (
                <div className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] text-green-700">
                  {t('dataSource.website.active', { ns: 'common' })}
                </div>
                )}
          </button>
        )
      })}
    </div>
  </div>
)

export const SetupManualHint = ({
  isZalo,
  t,
}: {
  isZalo: boolean
  t: TranslateFn
}) => (
  <div className="rounded-lg border border-divider-subtle bg-background-default px-3 py-2">
    <div className="mb-1 system-xs-semibold-uppercase text-text-tertiary">{t('settings.channelsManualSetupTitle', { ns: 'common' })}</div>
    <div className="system-xs-regular text-text-secondary">
      {isZalo ? t('settings.channelsZaloSetupHint', { ns: 'common' }) : t('settings.channelsGenericSetupHint', { ns: 'common' })}
    </div>
  </div>
)

export const SetupNavigation = ({
  setupStep,
  canGoNext,
  onBack,
  onNext,
  t,
}: {
  setupStep: SetupStep
  canGoNext: boolean
  onBack: () => void
  onNext: () => void
  t: TranslateFn
}) => (
  <div className="flex justify-between gap-2 pt-2">
    <Button disabled={setupStep === 1} onClick={onBack}>
      {t('operation.back', { ns: 'common' })}
    </Button>
    <Button variant="primary" disabled={!canGoNext || setupStep === 3} onClick={onNext}>
      {t('operation.continue', { ns: 'common' })}
    </Button>
  </div>
)

export const SetupSection = ({ children }: { children: ReactNode }) => <div className="space-y-2">{children}</div>
