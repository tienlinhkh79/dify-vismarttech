import type { MetadataRoute } from 'next'

const baseUrl = process.env.NEXT_PUBLIC_LANDING_URL || 'http://localhost:3001'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: '*', allow: '/' }],
    sitemap: `${baseUrl}/sitemap.xml`,
  }
}
