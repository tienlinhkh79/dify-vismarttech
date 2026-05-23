/**
 * Brand marks via Simple Icons CDN (MIT): https://simpleicons.org/
 * Use official colors; "Website" uses a neutral globe SVG.
 */

const si = (slug: string, color: string) =>
  `https://cdn.simpleicons.org/${slug}/${color.replace(/^#/, '')}`

const SLUG_COLOR: Record<string, string> = {
  lazada: '0F146F',
  zalo: '0068FF',
  facebook: '0866FF',
  instagram: 'E4405F',
  tiktok: '000000',
  meta: '0467DF',
}

function normalizeBrand(raw: string): string {
  return raw.trim().toLowerCase()
}

export function resolveBrandIcon(
  raw: string,
): { kind: 'img'; src: string } | { kind: 'globe' } | { kind: 'none' } {
  const n = normalizeBrand(raw)
  if (n === 'website' || n === 'web')
    return { kind: 'globe' }
  const color = SLUG_COLOR[n]
  if (color)
    return { kind: 'img', src: si(n, color) }
  return { kind: 'none' }
}

export function GlobeIcon({ className, size = 24 }: { className?: string; size?: number }) {
  return (
    <svg
      aria-hidden
      className={className}
      fill="none"
      height={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.75"
      viewBox="0 0 24 24"
      width={size}
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  )
}

type BrandIconProps = {
  name: string
  size?: number
  className?: string
}

export function BrandIcon({ name, size = 24, className }: BrandIconProps) {
  const spec = resolveBrandIcon(name)
  if (spec.kind === 'globe')
    return <GlobeIcon className={className} size={size} />
  if (spec.kind === 'img') {
    return (
      <img
        alt=""
        className={className}
        decoding="async"
        height={size}
        loading="lazy"
        referrerPolicy="no-referrer"
        src={spec.src}
        width={size}
      />
    )
  }
  return (
    <span aria-hidden className={className} style={{ fontSize: size * 0.45, fontWeight: 800 }}>
      {name.slice(0, 1)}
    </span>
  )
}

type HubChannelTileProps = {
  name: string
}

export function HubChannelTile({ name }: HubChannelTileProps) {
  return (
    <div aria-label={name} className="hub-channel-cell" role="img" title={name}>
      <BrandIcon className="hub-channel-icon" name={name} size={26} />
    </div>
  )
}
