import type { i18n as I18nInstance } from 'i18next'
import type { Locale } from '@/i18n-config/language'

import Cookies from 'js-cookie'
import { LOCALE_COOKIE_NAME } from '@/config'
import { changeLanguage } from '@/i18n-config/client'
import { LanguagesSupported } from '@/i18n-config/language'

export const i18n = {
  defaultLocale: 'en-US',
  locales: LanguagesSupported,
} as const

export { Locale }

/**
 * Updates locale cookie. When reloadPage is false, pass the active react-i18next
 * instance from useTranslation() so UI strings update immediately (getI18n() is not
 * the same instance as I18nextProvider when using createInstance()).
 */
export const setLocaleOnClient = async (
  locale: Locale,
  reloadPage = true,
  i18nInstance?: I18nInstance,
) => {
  Cookies.set(LOCALE_COOKIE_NAME, locale, { expires: 365 })
  if (reloadPage) {
    location.reload()
    return
  }
  if (i18nInstance)
    await i18nInstance.changeLanguage(locale)
  else
    await changeLanguage(locale)
}

export const renderI18nObject = (obj: Record<string, string>, language: string) => {
  if (!obj)
    return ''
  if (obj?.[language])
    return obj[language]
  if (obj?.en_US)
    return obj.en_US
  return Object.values(obj)[0]
}
