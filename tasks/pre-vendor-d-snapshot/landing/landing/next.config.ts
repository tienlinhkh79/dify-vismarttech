import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  // Avoid year-long HTML cache at the edge after deploy (chunk hashes change every build).
  async headers() {
    return [
      {
        source: '/((?!_next/static|_next/image|favicon.ico|logo/).*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, s-maxage=300, must-revalidate',
          },
        ],
      },
    ]
  },
  images: {
    // Alpine Docker images do not ship sharp; avoid 400 from /_next/image in production.
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'cdn.simpleicons.org',
        pathname: '/**',
      },
    ],
  },
}

export default nextConfig
