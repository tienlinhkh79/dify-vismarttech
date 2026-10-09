import { describe, expect, it } from 'vitest'
import {
  applyCannedResponse,
  extractSlashQuery,
  filterCannedResponses,
  getChannelMessageMaxLength,
  isMessagingWindowOpen,
  supportsComposerReplyTo,
  wrapComposerSelection,
} from './omnichannel-composer-utils'

describe('omnichannel-composer-utils', () => {
  it('returns channel max length', () => {
    expect(getChannelMessageMaxLength('facebook_messenger')).toBe(2000)
    expect(getChannelMessageMaxLength('unknown')).toBeNull()
  })

  it('supports reply-to on messenger channels', () => {
    expect(supportsComposerReplyTo('facebook_messenger')).toBe(true)
    expect(supportsComposerReplyTo('email')).toBe(false)
  })

  it('detects messaging window from last inbound', () => {
    const recent = new Date(Date.now() - 60_000).toISOString()
    const old = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString()
    expect(isMessagingWindowOpen(recent)).toBe(true)
    expect(isMessagingWindowOpen(old)).toBe(false)
  })

  it('filters canned responses by title or shortcut', () => {
    const items = [
      { id: '1', title: 'Greeting', content: 'Hello', shortcut: 'hi' },
      { id: '2', title: 'Shipping', content: 'We ship in 2 days', shortcut: 'ship' },
    ]
    expect(filterCannedResponses(items, 'ship')).toHaveLength(1)
    expect(filterCannedResponses(items, 'hi')).toHaveLength(1)
  })

  it('extracts slash query at cursor', () => {
    expect(extractSlashQuery('hello /gre', 10)).toEqual({ active: true, query: 'gre', start: 6 })
    expect(extractSlashQuery('hello/world', 5)).toEqual({ active: false, query: '', start: -1 })
  })

  it('applies canned response replacing slash token', () => {
    const result = applyCannedResponse('/gre', 0, 4, 'Xin chào!')
    expect(result.nextText).toBe('Xin chào!')
    expect(result.nextCursor).toBe(9)
  })

  it('wraps selection with bold markers', () => {
    const result = wrapComposerSelection('hello world', 6, 11, 'bold')
    expect(result.nextText).toBe('hello **world**')
  })
})
