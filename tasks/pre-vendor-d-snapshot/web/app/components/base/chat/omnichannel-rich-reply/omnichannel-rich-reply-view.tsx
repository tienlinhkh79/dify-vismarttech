'use client'

import type { FC, MouseEvent } from 'react'
import type {
  OmnichannelRichReplyButton,
  OmnichannelRichReplyCard,
  OmnichannelRichReplyPayload,
} from './types'
import { useTranslation } from '#i18n'
import { shouldAttemptRemoteImage } from '@/utils/omnichannel-remote-image'
import { cn } from '@/utils/classnames'

type OmnichannelRichReplyViewProps = {
  payload: OmnichannelRichReplyPayload
  variant?: 'default' | 'onAccent'
  onButtonClick?: (button: OmnichannelRichReplyButton) => void
}

function resolveCardLink(card: OmnichannelRichReplyCard): string {
  if (card.default_url?.trim())
    return card.default_url.trim()
  for (const button of card.buttons || []) {
    if (button.action === 'url' && button.url?.trim())
      return button.url.trim()
  }
  return ''
}

function RichReplyButton({
  button,
  variant,
  onButtonClick,
}: {
  button: OmnichannelRichReplyButton
  variant: 'default' | 'onAccent'
  onButtonClick?: (button: OmnichannelRichReplyButton) => void
}) {
  const isUrl = button.action === 'url' && !!button.url?.trim()
  const className = cn(
    'inline-flex max-w-full items-center justify-center rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
    variant === 'onAccent'
      ? 'bg-white/15 text-text-primary-on-surface ring-1 ring-white/25 hover:bg-white/25'
      : 'bg-background-default text-text-primary ring-1 ring-divider-subtle hover:bg-state-base-hover',
  )

  if (isUrl) {
    return (
      <a
        href={button.url}
        target="_blank"
        rel="noreferrer"
        className={className}
        onClick={(event: MouseEvent<HTMLAnchorElement>) => event.stopPropagation()}
      >
        {button.title}
      </a>
    )
  }

  return (
    <button
      type="button"
      className={className}
      onClick={() => onButtonClick?.(button)}
    >
      {button.title}
    </button>
  )
}

function ProductCard({
  card,
  variant,
  onButtonClick,
}: {
  card: OmnichannelRichReplyCard
  variant: 'default' | 'onAccent'
  onButtonClick?: (button: OmnichannelRichReplyButton) => void
}) {
  const { t } = useTranslation('common')
  const link = resolveCardLink(card)

  return (
    <article
      className={cn(
        'flex w-[min(220px,72vw)] shrink-0 flex-col overflow-hidden rounded-xl shadow-sm',
        variant === 'onAccent'
          ? 'bg-white/10 ring-1 ring-white/20'
          : 'bg-background-default ring-1 ring-divider-subtle',
      )}
    >
      {!!card.image_url && shouldAttemptRemoteImage(card.image_url) && (
        link
          ? (
              <a href={link} target="_blank" rel="noreferrer" className="block">
                <img
                  src={card.image_url}
                  alt={card.title}
                  className="aspect-[4/3] w-full object-cover"
                  loading="lazy"
                  decoding="async"
                  referrerPolicy="no-referrer"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                  }}
                />
              </a>
            )
          : (
              <img
                src={card.image_url}
                alt={card.title}
                className="aspect-[4/3] w-full object-cover"
                loading="lazy"
                decoding="async"
                referrerPolicy="no-referrer"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
            )
      )}
      <div className="flex flex-1 flex-col gap-2 p-3">
        <div className="space-y-1">
          <div className={cn(
            'line-clamp-2 text-sm font-semibold',
            variant === 'onAccent' ? 'text-text-primary-on-surface' : 'text-text-primary',
          )}
          >
            {card.title}
          </div>
          {!!card.subtitle && (
            <div className={cn(
              'text-xs',
              variant === 'onAccent' ? 'text-text-primary-on-surface/80' : 'text-text-secondary',
            )}
            >
              {card.subtitle}
            </div>
          )}
        </div>
        {(card.buttons?.length || link) && (
          <div className="mt-auto flex flex-wrap gap-2 pt-1">
            {(card.buttons || []).map(button => (
              <RichReplyButton
                key={`${button.title}-${button.payload || button.url || ''}`}
                button={button}
                variant={variant}
                onButtonClick={onButtonClick}
              />
            ))}
            {!card.buttons?.length && link && (
              <a
                href={link}
                target="_blank"
                rel="noreferrer"
                className={cn(
                  'inline-flex rounded-full px-3 py-1.5 text-sm font-medium',
                  variant === 'onAccent'
                    ? 'bg-white/15 text-text-primary-on-surface ring-1 ring-white/25 hover:bg-white/25'
                    : 'bg-state-base-hover text-text-accent ring-1 ring-divider-subtle',
                )}
              >
                {t('operation.viewDetails')}
              </a>
            )}
          </div>
        )}
      </div>
    </article>
  )
}

export const OmnichannelRichReplyView: FC<OmnichannelRichReplyViewProps> = ({
  payload,
  variant = 'default',
  onButtonClick,
}) => {
  const intro = payload.type === 'cards' ? payload.text?.trim() : payload.text.trim()
  const footerButtons = payload.type === 'cards' ? payload.buttons || [] : payload.buttons

  return (
    <div className="flex flex-col gap-3" data-testid="omnichannel-rich-reply">
      {!!intro && (
        <p className={cn(
          'whitespace-pre-wrap',
          variant === 'onAccent' ? 'text-text-primary-on-surface' : 'text-text-primary',
        )}
        >
          {intro}
        </p>
      )}
      {payload.type === 'cards' && payload.cards.length > 0 && (
        <div className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-1">
          {payload.cards.map(card => (
            <ProductCard
              key={`${card.title}-${card.image_url || ''}`}
              card={card}
              variant={variant}
              onButtonClick={onButtonClick}
            />
          ))}
        </div>
      )}
      {footerButtons.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {footerButtons.map(button => (
            <RichReplyButton
              key={`${button.title}-${button.payload || button.url || ''}`}
              button={button}
              variant={variant}
              onButtonClick={onButtonClick}
            />
          ))}
        </div>
      )}
    </div>
  )
}
