import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ZaloOAuthModal from '../zalo-oauth-modal'

vi.mock('@/service/tools', () => ({
  startZaloChannelOAuth: vi.fn().mockResolvedValue({
    data: {
      auth_url: 'https://oauth.zaloapp.com/v4/oa/permission?x=1',
      qr_data_uri: 'data:image/png;base64,AAA',
      state: 's',
      expires_in: 600,
      oauth_callback_url: 'https://example.com/triggers/zalo/oauth/callback',
    },
  }),
  getZaloChannelOAuthStatus: vi.fn().mockResolvedValue({ data: { connected: false } }),
}))

describe('ZaloOAuthModal', () => {
  it('renders nothing destructive when closed', () => {
    const t = (key: string) => key
    const { container } = render(
      <ZaloOAuthModal
        channelId={null}
        open={false}
        onClose={() => {}}
        onConnected={() => {}}
        t={t}
      />,
    )
    expect(container.querySelector('[role="dialog"]')).toBeNull()
  })
})
