import type { MetadataRoute } from 'next'

const baseUrl = process.env.NEXT_PUBLIC_LANDING_URL || 'http://localhost:3001'

export default function sitemap(): MetadataRoute.Sitemap {
  return ['/', '/features', '/pricing', '/contact'].map(path => ({
    url: `${baseUrl}${path}`,
    changeFrequency: 'weekly',
    priority: path === '/' ? 1 : 0.8,
  }))
}
