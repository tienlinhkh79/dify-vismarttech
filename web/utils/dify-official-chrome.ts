import { env } from '@/env'

/**
 * Whether to show Dify-operated marketing and support surfaces (community footer, account menu
 * external links, slash navigation to official docs/community, LangGenius auth footers).
 * Enterprise branding disables these without env; self-hosted SaaS can set
 * NEXT_PUBLIC_HIDE_COMMUNITY_UI=true as well.
 */
export function showDifyOfficialChrome(brandingEnabled: boolean): boolean {
  return !brandingEnabled && !env.NEXT_PUBLIC_HIDE_COMMUNITY_UI
}

/** Login/signup copy that avoids “Community Edition” phrasing when official chrome is suppressed. */
export function useEnterpriseStyleAuthChrome(brandingEnabled: boolean): boolean {
  return brandingEnabled || env.NEXT_PUBLIC_HIDE_COMMUNITY_UI
}
