'use client'

import { useCallback, useId, useLayoutEffect, useState, type RefObject } from 'react'

const DESKTOP_MQ = '(min-width: 768px)'

type HubAnchorId = 'hub' | 'chat' | 'channels' | 'remarketing' | 'security' | 'results'

type ConnectorSpec = {
  id: string
  side: 'left' | 'right'
  cardAnchor: HubAnchorId
  delay: string
}

/**
 * Visual QA (desktop): five orthogonal paths in gutters only —
 * chat, channels (hub edge → gutter mid → card), remarketing, security, results.
 * Each line: hub edge at card vertical center → horizontal through gutter mid → card inner edge.
 */
const CONNECTORS: ConnectorSpec[] = [
  { id: 'left-chat', side: 'left', cardAnchor: 'chat', delay: '0s' },
  { id: 'left-channels', side: 'left', cardAnchor: 'channels', delay: '0.4s' },
  { id: 'right-rm', side: 'right', cardAnchor: 'remarketing', delay: '0.12s' },
  { id: 'right-security', side: 'right', cardAnchor: 'security', delay: '0.5s' },
  { id: 'right-results', side: 'right', cardAnchor: 'results', delay: '0.72s' },
]

type MeasuredPath = {
  id: string
  d: string
  delay: string
}

type Rect = {
  left: number
  right: number
  midY: number
}

function measureAnchor(container: HTMLElement, anchor: HubAnchorId): Rect | null {
  const el = container.querySelector<HTMLElement>(`[data-hub-anchor="${anchor}"]`)
  if (!el)
    return null

  const c = container.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  if (r.width <= 0 || r.height <= 0)
    return null

  return {
    left: r.left - c.left,
    right: r.right - c.left,
    midY: r.top - c.top + r.height / 2,
  }
}

function measureGutterCenterX(container: HTMLElement, side: 'left' | 'right'): number | null {
  const selector = side === 'left' ? '.hero-hub-gutter--left' : '.hero-hub-gutter--right'
  const el = container.querySelector<HTMLElement>(selector)
  if (!el)
    return null

  const c = container.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  if (r.width <= 0)
    return null

  return r.left - c.left + r.width / 2
}

/** Fallback gutter midpoint between hub face and peripheral card inner edge. */
function gutterMidX(hub: Rect, card: Rect, side: 'left' | 'right'): number {
  if (side === 'left')
    return (hub.left + card.right) / 2
  return (hub.right + card.left) / 2
}

/**
 * Left column: hub.left → gutter → card.right at card midY.
 * Right column: hub.right → gutter → card.left at card midY.
 */
function buildOrthogonalPath(
  hub: Rect,
  card: Rect,
  side: 'left' | 'right',
  gutterCenterX: number,
): string {
  const y = card.midY

  if (side === 'left')
    return `M ${hub.left} ${y} L ${gutterCenterX} ${y} L ${card.right} ${y}`

  return `M ${hub.right} ${y} L ${gutterCenterX} ${y} L ${card.left} ${y}`
}

function measurePaths(container: HTMLElement): { paths: MeasuredPath[]; size: { width: number; height: number } } {
  const bounds = container.getBoundingClientRect()
  const size = {
    width: Math.max(bounds.width, 1),
    height: Math.max(bounds.height, 1),
  }

  const hub = measureAnchor(container, 'hub')
  if (!hub)
    return { paths: [], size }

  const leftGutterX = measureGutterCenterX(container, 'left')
  const rightGutterX = measureGutterCenterX(container, 'right')

  const paths: MeasuredPath[] = []
  for (const spec of CONNECTORS) {
    const card = measureAnchor(container, spec.cardAnchor)
    if (!card)
      continue

    const measuredGutter = spec.side === 'left' ? leftGutterX : rightGutterX
    const gutterCenterX = measuredGutter ?? gutterMidX(hub, card, spec.side)

    paths.push({
      id: spec.id,
      d: buildOrthogonalPath(hub, card, spec.side, gutterCenterX),
      delay: spec.delay,
    })
  }

  return { paths, size }
}

type HubConnectorLinesProps = {
  containerRef: RefObject<HTMLElement | null>
}

export function HubConnectorLines({ containerRef }: HubConnectorLinesProps) {
  const gradientId = useId().replace(/:/g, '')
  const [paths, setPaths] = useState<MeasuredPath[]>([])
  const [size, setSize] = useState({ width: 0, height: 0 })

  const measure = useCallback(() => {
    const container = containerRef.current
    if (!container || typeof window === 'undefined')
      return

    if (!window.matchMedia(DESKTOP_MQ).matches) {
      setPaths([])
      setSize({ width: 0, height: 0 })
      return
    }

    const { paths: next, size: nextSize } = measurePaths(container)
    setPaths(next)
    setSize(nextSize)
  }, [containerRef])

  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container)
      return

    const scheduleMeasure = () => {
      requestAnimationFrame(() => {
        measure()
        requestAnimationFrame(measure)
      })
    }

    measure()
    scheduleMeasure()

    const ro = new ResizeObserver(() => scheduleMeasure())
    ro.observe(container)
    for (const anchor of container.querySelectorAll('[data-hub-anchor]'))
      ro.observe(anchor)

    for (const gutter of container.querySelectorAll('.hero-hub-gutter'))
      ro.observe(gutter)

    const mq = window.matchMedia(DESKTOP_MQ)
    const onMq = () => scheduleMeasure()
    mq.addEventListener('change', onMq)
    window.addEventListener('resize', scheduleMeasure)
    window.addEventListener('load', scheduleMeasure)
    document.fonts?.ready?.then(scheduleMeasure)

    for (const img of container.querySelectorAll('img')) {
      if (!img.complete)
        img.addEventListener('load', scheduleMeasure, { once: true })
    }

    const delayed = [80, 250, 600].map(ms => window.setTimeout(scheduleMeasure, ms))

    return () => {
      ro.disconnect()
      mq.removeEventListener('change', onMq)
      window.removeEventListener('resize', scheduleMeasure)
      window.removeEventListener('load', scheduleMeasure)
      delayed.forEach(clearTimeout)
    }
  }, [containerRef, measure])

  if (paths.length === 0 || size.width <= 0 || size.height <= 0)
    return null

  return (
    <svg
      aria-hidden
      className="hero-hub-lines"
      preserveAspectRatio="none"
      viewBox={`0 0 ${size.width} ${size.height}`}
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" x2="100%" y1="0%" y2="0%">
          <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
          <stop offset="42%" stopColor="#818cf8" stopOpacity="1" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0.4" />
        </linearGradient>
      </defs>
      <g className="hub-lines-track">
        {paths.map(path => (
          <path key={`track-${path.id}`} d={path.d} />
        ))}
      </g>
      <g className="hub-lines-energy">
        {paths.map(path => (
          <path
            key={`flow-${path.id}`}
            className="hub-line-pulse"
            d={path.d}
            stroke={`url(#${gradientId})`}
            style={{ animationDelay: path.delay }}
          />
        ))}
      </g>
    </svg>
  )
}
