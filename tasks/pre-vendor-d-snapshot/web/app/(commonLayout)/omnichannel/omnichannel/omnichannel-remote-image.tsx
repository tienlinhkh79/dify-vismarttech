'use client'

import type { ReactNode } from 'react'
import { useState } from 'react'
import {
  isRemoteImageFailed,
  markRemoteImageFailed,
  resolveAvatarImageUrl,
  shouldAttemptRemoteImage,
} from '@/utils/omnichannel-remote-image'

export function OmnichannelAvatar({
  imageUrl,
  initials,
  size = 32,
}: {
  imageUrl?: string | null
  initials: string
  size?: number
}) {
  const [imageFailedForUrl, setImageFailedForUrl] = useState<string | null>(null)
  const label = (initials || '?').slice(0, 2).toUpperCase()
  const trimmedUrl = resolveAvatarImageUrl(imageUrl)
  const imageFailed = !!trimmedUrl && (imageFailedForUrl === trimmedUrl || isRemoteImageFailed(trimmedUrl))
  const showImage = Boolean(trimmedUrl) && !imageFailed

  return (
    <div
      className="shrink-0 overflow-hidden rounded-full border border-divider-subtle bg-background-default shadow-sm"
      style={{ width: size, height: size }}
    >
      {showImage
        ? (
            <img
              src={trimmedUrl!}
              alt=""
              loading="lazy"
              decoding="async"
              referrerPolicy="no-referrer"
              className="size-full object-cover"
              onError={() => {
                markRemoteImageFailed(trimmedUrl!)
                setImageFailedForUrl(trimmedUrl)
              }}
            />
          )
        : (
            <div className="flex size-full items-center justify-center text-[10px] font-semibold text-text-tertiary">
              {label}
            </div>
          )}
    </div>
  )
}

export function SafeRemoteImage({
  src,
  alt,
  className,
  fallback,
}: {
  src: string
  alt: string
  className?: string
  fallback?: ReactNode
}) {
  const [failed, setFailed] = useState(() => !shouldAttemptRemoteImage(src))
  const canLoad = shouldAttemptRemoteImage(src) && !failed

  if (!canLoad) {
    return (
      <>
        {fallback ?? (
          <div className={className || 'rounded-lg border border-divider-subtle bg-background-default p-2 text-xs text-text-tertiary'}>
            —
          </div>
        )}
      </>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      className={className}
      onError={() => {
        markRemoteImageFailed(src)
        setFailed(true)
      }}
    />
  )
}
