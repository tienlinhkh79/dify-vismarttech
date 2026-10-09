export type OmnichannelRichReplyButton = {
  title: string
  action: 'url' | 'postback'
  url?: string
  payload?: string
  image_url?: string
}

export type OmnichannelRichReplyCard = {
  title: string
  subtitle?: string
  image_url?: string
  default_url?: string
  buttons?: OmnichannelRichReplyButton[]
}

export type OmnichannelRichReplyPayload =
  | {
    type: 'actions'
    text: string
    buttons: OmnichannelRichReplyButton[]
  }
  | {
    type: 'cards'
    text?: string
    cards: OmnichannelRichReplyCard[]
    buttons?: OmnichannelRichReplyButton[]
  }
