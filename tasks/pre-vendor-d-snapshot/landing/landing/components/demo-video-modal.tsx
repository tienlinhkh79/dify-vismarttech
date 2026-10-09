'use client'

import { useEffect } from 'react'

export const DEMO_VIDEO_EMBED_URL = 'https://www.youtube.com/embed/dQw4w9WgXcQ'

type DemoVideoModalProps = {
  open: boolean
  onClose: () => void
  title: string
  closeLabel: string
  embedUrl?: string
}

function CloseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  )
}

export default function DemoVideoModal({
  open,
  onClose,
  title,
  closeLabel,
  embedUrl = DEMO_VIDEO_EMBED_URL,
}: DemoVideoModalProps) {
  useEffect(() => {
    if (!open)
      return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape')
        onClose()
    }

    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open, onClose])

  if (!open)
    return null

  return (
    <div
      className="demo-modal-overlay"
      onClick={onClose}
      role="presentation"
    >
      <div
        aria-labelledby="demo-video-modal-title"
        aria-modal="true"
        className="demo-modal card"
        onClick={event => event.stopPropagation()}
        role="dialog"
      >
        <div className="demo-modal-header">
          <h2 className="demo-modal-title" id="demo-video-modal-title">
            {title}
          </h2>
          <button
            aria-label={closeLabel}
            className="icon-button demo-modal-close"
            onClick={onClose}
            type="button"
          >
            <CloseIcon />
          </button>
        </div>
        <div className="demo-modal-video">
          <iframe
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
            src={embedUrl}
            title={title}
          />
        </div>
      </div>
    </div>
  )
}
