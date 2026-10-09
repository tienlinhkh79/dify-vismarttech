import { describe, expect, it } from 'vitest'
import { legacySlugLabel, parseOmnichannelRichReply, slugLabel } from './parse-omnichannel-rich-reply'

describe('slugLabel', () => {
  it('folds Vietnamese diacritics like workflow format node', () => {
    expect(slugLabel('Xem quy trình')).toBe('xem_quy_trinh')
    expect(legacySlugLabel('Xem quy trình')).toBe('xem_quy_tr_nh')
  })
})

describe('parseOmnichannelRichReply', () => {
  it('parses cards payload from workflow answer', () => {
    const payload = parseOmnichannelRichReply(JSON.stringify({
      type: 'cards',
      text: 'Dạ, tôi gửi bạn một số mẫu giao diện có hình ảnh đại diện từ website để bạn tham khảo nhé:',
      cards: [
        {
          title: 'Mẫu shop bán hàng 02',
          image_url: 'https://vietautomate.com/wp-content/uploads/2018/12/shop2.jpg',
          subtitle: '1.000.000đ',
          default_url: 'https://vietautomate.com/mau-shop-ban-hang-02/',
          buttons: [{ title: 'Xem chi tiết', action: 'url', url: 'https://vietautomate.com/mau-shop-ban-hang-02/' }],
        },
      ],
      buttons: [{ title: 'Xem thêm mẫu', action: 'postback', payload: 'xem_them' }],
    }))

    expect(payload?.type).toBe('cards')
    if (payload?.type !== 'cards')
      return
    expect(payload.text).toContain('mẫu giao diện')
    expect(payload.cards).toHaveLength(1)
    expect(payload.cards[0].image_url).toContain('shop2.jpg')
    expect(payload.buttons).toHaveLength(1)
  })

  it('parses actions payload', () => {
    const payload = parseOmnichannelRichReply(JSON.stringify({
      type: 'actions',
      text: 'Bạn chọn giúp em:',
      buttons: [{ title: 'Liên hệ', action: 'postback', payload: 'lien_he' }],
    }))

    expect(payload).toEqual({
      type: 'actions',
      text: 'Bạn chọn giúp em:',
      buttons: [{ title: 'Liên hệ', action: 'postback', payload: 'lien_he' }],
    })
  })

  it('returns null for plain text', () => {
    expect(parseOmnichannelRichReply('Xin chào bạn')).toBeNull()
  })

  it('parses llm structured output leak without type field', () => {
    const payload = parseOmnichannelRichReply(JSON.stringify({
      ai_reply: 'Dạ, anh/chị có thể liên hệ qua hotline 079 777 6900.',
      display_type: 'text_only',
      products: [],
      quick_replies: ['Gọi hotline', 'Nhắn Zalo tư vấn'],
    }))

    expect(payload?.type).toBe('actions')
    if (payload?.type !== 'actions')
      return
    expect(payload.text).toContain('hotline')
    expect(payload.buttons).toHaveLength(2)
    expect(payload.buttons[0].title).toBe('Gọi hotline')
    expect(payload.buttons[0].payload).toBe('goi_hotline')
  })

  it('unwraps actions whose text field contains structured json leak', () => {
    const payload = parseOmnichannelRichReply(JSON.stringify({
      type: 'actions',
      text: JSON.stringify({
        ai_reply: 'Nội dung sạch',
        display_type: 'text_only',
        quick_replies: ['Liên hệ'],
      }),
      buttons: [
        { title: 'Tư vấn thêm', action: 'postback', payload: 'tu_van' },
      ],
    }))

    expect(payload?.type).toBe('actions')
    if (payload?.type !== 'actions')
      return
    expect(payload.text).toBe('Nội dung sạch')
    expect(payload.buttons[0].title).toBe('Liên hệ')
  })
})
