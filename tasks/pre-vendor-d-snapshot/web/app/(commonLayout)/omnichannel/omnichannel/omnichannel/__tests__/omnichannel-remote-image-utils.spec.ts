import { describe, expect, it } from 'vitest'
import {
  isMetaCdnImageUrl,
  markRemoteImageFailed,
  resolveAvatarImageUrl,
  shouldAttemptRemoteImage,
} from '@/utils/omnichannel-remote-image'

describe('omnichannel-remote-image-utils', () => {
  it('detects Meta CDN hosts', () => {
    expect(isMetaCdnImageUrl('https://scontent.fsgn8-1.fna.fbcdn.net/v/t1.0-1/x.png')).toBe(true)
    expect(isMetaCdnImageUrl('https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=1')).toBe(true)
    expect(isMetaCdnImageUrl('https://cdn.zalo.me/avatar.jpg')).toBe(false)
  })

  it('skips Meta CDN for avatars and attachments', () => {
    const fb = 'https://scontent.fsgm13-2.fna.fbcdn.net/v/t39.30808-1/foo.png'
    expect(resolveAvatarImageUrl(fb)).toBeNull()
    expect(shouldAttemptRemoteImage(fb)).toBe(false)
    expect(resolveAvatarImageUrl('https://cdn.example.com/a.jpg')).toBe('https://cdn.example.com/a.jpg')
  })

  it('remembers failed non-Meta URLs', () => {
    const url = `https://cdn.example.com/fail-${Date.now()}.jpg`
    expect(shouldAttemptRemoteImage(url)).toBe(true)
    markRemoteImageFailed(url)
    expect(shouldAttemptRemoteImage(url)).toBe(false)
    expect(resolveAvatarImageUrl(url)).toBeNull()
  })
})
