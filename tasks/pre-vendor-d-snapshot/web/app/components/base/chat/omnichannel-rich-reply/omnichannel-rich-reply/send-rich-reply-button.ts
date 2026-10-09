import type { OnSend } from '../types'
import type { OmnichannelRichReplyButton } from './types'

export function sendRichReplyButton(
  onSend: OnSend,
  button: OmnichannelRichReplyButton,
): void {
  const display = button.title.trim()
  if (!display)
    return

  const payload = button.payload?.trim()
  const options = payload && payload !== display
    ? { routingQuery: payload }
    : undefined

  onSend(display, [], false, null, options)
}
