'use client'
import type { ActionItem } from '../types'
import { useTheme } from 'next-themes'
import { useEffect } from 'react'
import { getI18n, useTranslation } from 'react-i18next'
import type { Locale } from '@/i18n-config'
import { setLocaleOnClient } from '@/i18n-config'
import { useGlobalPublicStore } from '@/context/global-public-context'
import { showDifyOfficialChrome } from '@/utils/dify-official-chrome'
import { accountCommand } from './account'
import { executeCommand } from './command-bus'
import { communityCommand } from './community'
import { docsCommand } from './docs'
import { forumCommand } from './forum'
import { languageCommand } from './language'
import { slashCommandRegistry } from './registry'
import { themeCommand } from './theme'
import { zenCommand } from './zen'

export const slashAction: ActionItem = {
  key: '/',
  shortcut: '/',
  get title() {
    const i18n = getI18n()
    return i18n.t('gotoAnything.actions.slashTitle', { ns: 'app' })
  },
  get description() {
    const i18n = getI18n()
    return i18n.t('gotoAnything.actions.slashDesc', { ns: 'app' })
  },
  action: (result) => {
    if (result.type !== 'command')
      return
    const { command, args } = result.data
    executeCommand(command, args)
  },
  search: async (query, _searchTerm = '') => {
    const i18n = getI18n()
    // Delegate all search logic to the command registry system
    return slashCommandRegistry.search(query, i18n.language)
  },
}

// Register/unregister default handlers for slash commands with external dependencies.
const registerSlashCommands = (deps: { setTheme: (t: string) => void, setLocale: (locale: string) => void, showOfficialDifyChrome: boolean }) => {
  slashCommandRegistry.register(themeCommand, { setTheme: deps.setTheme })
  slashCommandRegistry.register(languageCommand, { setLocale: deps.setLocale })
  if (deps.showOfficialDifyChrome) {
    slashCommandRegistry.register(forumCommand, {})
    slashCommandRegistry.register(docsCommand, {})
    slashCommandRegistry.register(communityCommand, {})
  }
  slashCommandRegistry.register(accountCommand, {})
  slashCommandRegistry.register(zenCommand, {})
}

const unregisterSlashCommands = (showOfficialDifyChrome: boolean) => {
  slashCommandRegistry.unregister('theme')
  slashCommandRegistry.unregister('language')
  if (showOfficialDifyChrome) {
    slashCommandRegistry.unregister('forum')
    slashCommandRegistry.unregister('docs')
    slashCommandRegistry.unregister('community')
  }
  slashCommandRegistry.unregister('account')
  slashCommandRegistry.unregister('zen')
}

export const SlashCommandProvider = () => {
  const theme = useTheme()
  const { i18n } = useTranslation()
  const brandingEnabled = useGlobalPublicStore(s => s.systemFeatures.branding.enabled)
  const showOfficialDifyChrome = showDifyOfficialChrome(brandingEnabled)
  useEffect(() => {
    registerSlashCommands({
      setTheme: theme.setTheme,
      setLocale: (locale: string) => setLocaleOnClient(locale as Locale, false, i18n),
      showOfficialDifyChrome,
    })
    return () => unregisterSlashCommands(showOfficialDifyChrome)
  }, [theme.setTheme, i18n, showOfficialDifyChrome])

  return null
}
