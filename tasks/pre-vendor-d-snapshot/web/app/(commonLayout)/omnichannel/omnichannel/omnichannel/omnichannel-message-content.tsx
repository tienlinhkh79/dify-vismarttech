'use client'

import {
  OmnichannelRichReplyView,
  parseOmnichannelRichReply,
} from '@/app/components/base/chat/omnichannel-rich-reply'
import { cn } from '@/utils/classnames'

type OmnichannelMessageContentProps = {
  content: string
  emptyLabel: string
  variant?: 'default' | 'onAccent'
}

export function OmnichannelMessageContent({
  content,
  emptyLabel,
  variant = 'default',
}: OmnichannelMessageContentProps) {
  const richReply = parseOmnichannelRichReply(content)
  if (richReply) {
    return (
      <OmnichannelRichReplyView
        payload={richReply}
        variant={variant}
      />
    )
  }

  return (
    <div className={cn(
      'break-words whitespace-pre-wrap',
      variant === 'onAccent' ? 'text-text-primary-on-surface' : 'text-text-primary',
    )}
    >
      {content || emptyLabel}
    </div>
  )
}
