'use client'

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Lang } from '@/content/i18n'

type ThemeMode = 'light' | 'dark'

type PreferencesContextValue = {
  lang: Lang
  setLang: (lang: Lang) => void
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null)

type PreferencesProviderProps = {
  children: ReactNode
}

export function PreferencesProvider({ children }: PreferencesProviderProps) {
  const [lang, setLang] = useState<Lang>('vi')
  const [theme, setTheme] = useState<ThemeMode>('light')

  useEffect(() => {
    const savedLang = localStorage.getItem('landing.lang') as Lang | null
    const savedTheme = localStorage.getItem('landing.theme') as ThemeMode | null
    if (savedLang === 'vi' || savedLang === 'en')
      setLang(savedLang)
    if (savedTheme === 'light' || savedTheme === 'dark')
      setTheme(savedTheme)
  }, [])

  useEffect(() => {
    localStorage.setItem('landing.lang', lang)
  }, [lang])

  useEffect(() => {
    localStorage.setItem('landing.theme', theme)
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const value = useMemo(() => ({ lang, setLang, theme, setTheme }), [lang, theme])
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>
}

export function usePreferences() {
  const context = useContext(PreferencesContext)
  if (!context)
    throw new Error('usePreferences must be used within PreferencesProvider')
  return context
}
