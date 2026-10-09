import { describe, expect, it } from 'vitest'
import { sendRichReplyButton } from './send-rich-reply-button'

describe('sendRichReplyButton', () => {
  it('shows button title and routes workflow with payload when they differ', () => {
    const onSend = vi.fn()
    sendRichReplyButton(onSend, {
      title: 'Liên hệ',
      action: 'postback',
      payload: 'lien_he',
    })

    expect(onSend).toHaveBeenCalledWith(
      'Liên hệ',
      [],
      false,
      null,
      { routingQuery: 'lien_he' },
    )
  })

  it('uses title only when payload matches title', () => {
    const onSend = vi.fn()
    sendRichReplyButton(onSend, {
      title: 'Liên hệ',
      action: 'postback',
      payload: 'Liên hệ',
    })

    expect(onSend).toHaveBeenCalledWith('Liên hệ', [], false, null, undefined)
  })

  it('routes auto-generated Vietnamese slugs while showing title', () => {
    const onSend = vi.fn()
    sendRichReplyButton(onSend, {
      title: 'Xem quy trình',
      action: 'postback',
      payload: 'xem_quy_trinh',
    })

    expect(onSend).toHaveBeenCalledWith(
      'Xem quy trình',
      [],
      false,
      null,
      { routingQuery: 'xem_quy_trinh' },
    )
  })

  it('ignores empty titles', () => {
    const onSend = vi.fn()
    sendRichReplyButton(onSend, {
      title: '   ',
      action: 'postback',
      payload: 'x',
    })

    expect(onSend).not.toHaveBeenCalled()
  })
})
