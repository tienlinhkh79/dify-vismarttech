export type ProviderSetupConfig = {
  requiresClientSecret: boolean
  requiresAccessToken: boolean
  requiresOAuthQR?: boolean
  showApiVersion: boolean
  resourceHintKey?: string
  docsUrl?: string
}

const MESSENGER_DOCS_URL = 'https://developers.facebook.com/docs/messenger-platform/webhooks/'
const INSTAGRAM_DOCS_URL = 'https://developers.facebook.com/docs/instagram-messaging/webhooks/'
const TIKTOK_DOCS_URL = 'https://business-api.tiktok.com/portal/bm-api/education-hub'
const ZALO_DOCS_URL = 'https://developers.zalo.me/docs/api/official-account-api/introduction/overview'

const PROVIDER_SETUP_CONFIG: Record<string, ProviderSetupConfig> = {
  facebook_messenger: {
    requiresClientSecret: false,
    requiresAccessToken: false,
    showApiVersion: false,
    resourceHintKey: 'settings.channelsFacebookPageIdHint',
    docsUrl: MESSENGER_DOCS_URL,
  },
  instagram_dm: {
    requiresClientSecret: true,
    requiresAccessToken: true,
    showApiVersion: true,
    resourceHintKey: 'settings.channelsInstagramResourceHint',
    docsUrl: INSTAGRAM_DOCS_URL,
  },
  tiktok_messaging: {
    requiresClientSecret: true,
    requiresAccessToken: true,
    showApiVersion: true,
    resourceHintKey: 'settings.channelsTikTokResourceHint',
    docsUrl: TIKTOK_DOCS_URL,
  },
  zalo_oa: {
    requiresClientSecret: true,
    requiresAccessToken: false,
    requiresOAuthQR: true,
    showApiVersion: false,
    resourceHintKey: 'settings.channelsZaloResourceHint',
    docsUrl: ZALO_DOCS_URL,
  },
}

const DEFAULT_PROVIDER_SETUP_CONFIG: ProviderSetupConfig = {
  requiresClientSecret: true,
  requiresAccessToken: false,
  showApiVersion: false,
}

export const getProviderSetupConfig = (channelType: string): ProviderSetupConfig => {
  return PROVIDER_SETUP_CONFIG[channelType] || DEFAULT_PROVIDER_SETUP_CONFIG
}
