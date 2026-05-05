import type { Metadata } from 'next'
import { PreferencesProvider } from '@/components/preferences-context'
import { siteContent } from '@/content/site'
import './globals.css'

export const metadata: Metadata = {
  title: `${siteContent.company} - AI Platform`,
  description: siteContent.description,
  metadataBase: new URL('http://localhost:3001'),
  openGraph: {
    title: `${siteContent.company} - AI Platform`,
    description: siteContent.description,
    type: 'website',
  },
}

type RootLayoutProps = Readonly<{
  children: React.ReactNode
}>

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <PreferencesProvider>{children}</PreferencesProvider>
      </body>
    </html>
  )
}
