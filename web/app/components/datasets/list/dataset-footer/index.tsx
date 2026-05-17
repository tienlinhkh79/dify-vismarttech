'use client'

import { RiInformationFill } from '@remixicon/react'
import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/utils/classnames'

const DatasetFooter = () => {
  const { t } = useTranslation()

  return (
    <footer className="shrink-0 px-6 pb-8 pt-2 md:px-12">
      <div
        className={cn(
          'flex gap-4 rounded-xl border border-divider-regular px-4 py-4 md:px-5 md:py-5',
          'bg-gradient-to-r from-state-accent-hover/80 via-background-default-subtle to-background-default-subtle',
        )}
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-text-accent/15 text-text-accent">
          <RiInformationFill className="h-5 w-5" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="system-md-semibold text-text-primary md:text-base">
            {t('didYouKnow', { ns: 'dataset' })}
          </h3>
          <p className="mt-1 system-sm-regular leading-relaxed text-text-secondary md:system-md-regular">
            {t('intro1', { ns: 'dataset' })}
            <span className="text-text-accent">{t('intro2', { ns: 'dataset' })}</span>
            {t('intro3', { ns: 'dataset' })}
            <br />
            {t('intro4', { ns: 'dataset' })}
            <span className="text-text-accent">{t('intro5', { ns: 'dataset' })}</span>
            {t('intro6', { ns: 'dataset' })}
          </p>
        </div>
      </div>
    </footer>
  )
}

export default React.memo(DatasetFooter)
