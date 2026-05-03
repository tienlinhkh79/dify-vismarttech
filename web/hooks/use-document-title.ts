'use client'
import { useFavicon, useTitle } from 'ahooks'
import { useEffect } from 'react'
import { APP_DISPLAY_NAME } from '@/config/app-display-name'
import { useGlobalPublicStore, useIsSystemFeaturesPending } from '@/context/global-public-context'
import { basePath } from '@/utils/var'

export default function useDocumentTitle(title: string) {
  const isPending = useIsSystemFeaturesPending()
  const systemFeatures = useGlobalPublicStore(s => s.systemFeatures)
  const prefix = title ? `${title} - ` : ''
  let titleStr = ''
  let favicon = ''
  if (isPending === false) {
    if (systemFeatures.branding.enabled) {
      titleStr = `${prefix}${systemFeatures.branding.application_title}`
      favicon = systemFeatures.branding.favicon?.trim() || `${basePath}/logo/logo.png`
    }
    else {
      titleStr = `${prefix}${APP_DISPLAY_NAME}`
      favicon = `${basePath}/logo/logo.png`
    }
  }
  useTitle(titleStr)
  useEffect(() => {
    let apple: HTMLLinkElement | null = null
    if (systemFeatures.branding.favicon) {
      document
        .querySelectorAll(
          'link[rel=\'icon\'], link[rel=\'shortcut icon\'], link[rel=\'apple-touch-icon\'], link[rel=\'mask-icon\']',
        )
        .forEach(n => n.parentNode?.removeChild(n))

      apple = document.createElement('link')
      apple.rel = 'apple-touch-icon'
      apple.href = systemFeatures.branding.favicon
      document.head.appendChild(apple)
    }

    return () => {
      apple?.remove()
    }
  }, [systemFeatures.branding.favicon])
  useFavicon(favicon)
}
