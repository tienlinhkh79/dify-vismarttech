'use client'
import type { Collection } from '@/app/components/tools/types'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import { toast } from '@/app/components/base/ui/toast'
import ConfigCredential from '@/app/components/tools/setting/build-in/config-credentials'
import ToolProviderList from '@/app/components/tools/provider-list'
import { CollectionType } from '@/app/components/tools/types'
import {
  fetchBuiltInToolCredential,
  listMessengerOmnichannelChannels,
  removeBuiltInToolCredential,
  updateBuiltInToolCredential,
} from '@/service/tools'
import {
  useAllToolProviders,
  useInvalidateAllToolProviders,
} from '@/service/use-tools'

const ToolsPage = () => {
  const { t } = useTranslation()
  const { data: providers = [] } = useAllToolProviders()
  const invalidateProviders = useInvalidateAllToolProviders()
  const [editingProvider, setEditingProvider] = useState<Collection | null>(null)
  const [providerConfiguredMap, setProviderConfiguredMap] = useState<Record<string, boolean>>({})

  const credentialProviders = useMemo(() => {
    const pinned = ['messenger', 'kiotviet']
    const builtIns = providers.filter(item => item.type === CollectionType.builtIn)
    const pinnedSet = new Set(pinned)

    return builtIns
      .filter(item => pinned.some(name => item.name === name || item.name.endsWith(`/${name}`)) || item.is_team_authorization)
      .sort((a, b) => {
        const aPinned = pinnedSet.has(a.name) || pinned.some(name => a.name.endsWith(`/${name}`))
        const bPinned = pinnedSet.has(b.name) || pinned.some(name => b.name.endsWith(`/${name}`))
        if (aPinned !== bPinned)
          return aPinned ? -1 : 1
        return a.label.en_US.localeCompare(b.label.en_US)
      })
  }, [providers])

  useEffect(() => {
    let cancelled = false

    const loadConfiguredState = async () => {
      if (!credentialProviders.length) {
        setProviderConfiguredMap({})
        return
      }

      const isNonEmptyCredential = (value: unknown) => {
        if (!value || typeof value !== 'object')
          return false
        return Object.values(value as Record<string, unknown>).some((item) => {
          if (typeof item === 'string')
            return item.trim().length > 0
          if (typeof item === 'number' || typeof item === 'boolean')
            return true
          return false
        })
      }

      const messengerProvider = credentialProviders.find(item => item.name === 'messenger' || item.name.endsWith('/messenger'))
      const messengerChannelsPromise = messengerProvider
        ? listMessengerOmnichannelChannels().then(res => (res.data || []).length > 0).catch(() => false)
        : Promise.resolve(false)

      const messengerChannelsConfigured = await messengerChannelsPromise
      const result = await Promise.all(
        credentialProviders.map(async (provider) => {
          const isMessenger = provider.name === 'messenger' || provider.name.endsWith('/messenger')
          try {
            const credential = await fetchBuiltInToolCredential(provider.name)
            const credentialConfigured = isNonEmptyCredential(credential)
            return [provider.id, provider.is_team_authorization || credentialConfigured || (isMessenger && messengerChannelsConfigured)] as const
          }
          catch {
            return [provider.id, provider.is_team_authorization || (isMessenger && messengerChannelsConfigured)] as const
          }
        }),
      )

      if (cancelled)
        return

      setProviderConfiguredMap(Object.fromEntries(result))
    }

    loadConfiguredState()

    return () => {
      cancelled = true
    }
  }, [credentialProviders])

  return (
    <div className="flex h-[calc(100vh-220px)] min-h-[520px] flex-col gap-3">
      <div className="rounded-xl border border-components-panel-border bg-components-panel-bg px-4 py-3">
        <div className="mb-1 system-sm-semibold text-text-primary">Credential Management</div>
        <div className="mb-3 system-xs-regular text-text-tertiary">
          Manage and verify configured tool credentials (for example Messenger and KiotViet).
        </div>
        {!credentialProviders.length && (
          <div className="system-xs-regular text-text-tertiary">No configured built-in tool credentials yet.</div>
        )}
        {!!credentialProviders.length && (
          <div className="space-y-2">
            {credentialProviders.map(provider => (
              <div
                key={provider.id}
                className="flex items-center justify-between rounded-lg border border-divider-subtle px-3 py-2"
              >
                {(() => {
                  const configured = providerConfiguredMap[provider.id] ?? provider.is_team_authorization
                  return (
                    <>
                      <div>
                        <div className="system-sm-medium text-text-primary">{provider.label.en_US}</div>
                        <div className="mt-0.5 system-xs-regular text-text-tertiary">
                          {configured ? 'Configured' : 'Not configured'}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="small"
                          variant="secondary"
                          onClick={() => setEditingProvider(provider)}
                        >
                          {configured ? t('operation.edit', { ns: 'common' }) : t('dataSource.configure', { ns: 'common' })}
                        </Button>
                      </div>
                    </>
                  )
                })()}
              </div>
            ))}
          </div>
        )}
      </div>
      <ToolProviderList />
      {editingProvider && (
        <ConfigCredential
          key={editingProvider.id}
          collection={editingProvider}
          onCancel={() => setEditingProvider(null)}
          onSaved={async (value) => {
            await updateBuiltInToolCredential(editingProvider.name, value)
            toast.success(t('api.actionSuccess', { ns: 'common' }))
            await invalidateProviders()
            setEditingProvider(null)
          }}
          onRemove={async () => {
            await removeBuiltInToolCredential(editingProvider.name)
            toast.success(t('api.actionSuccess', { ns: 'common' }))
            await invalidateProviders()
            setEditingProvider(null)
          }}
        />
      )}
    </div>
  )
}

export default ToolsPage
