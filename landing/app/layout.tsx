import type { Metadata } from 'next'
import { PreferencesProvider } from '@/components/preferences-context'
import { siteContent } from '@/content/site'
import './globals.css'

export const metadata: Metadata = {
  title: `${siteContent.company} - AI Platform`,
  description: siteContent.description,
  metadataBase: new URL(process.env.NEXT_PUBLIC_LANDING_URL || 'http://chatbotai.vismarttech.com'),
  icons: {
    icon: '/logo/logo.png',
    shortcut: '/logo/logo.png',
    apple: '/logo/logo.png',
  },
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
