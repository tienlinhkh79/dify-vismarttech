'use client'
import {
  RiAddLine,
} from '@remixicon/react'
import * as React from 'react'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { cn } from '@/utils/classnames'

const NewDatasetCard = () => {
  const { t } = useTranslation()

  return (
    <div
      className={cn(
        'group relative col-span-1 flex h-[190px] flex-col rounded-xl border border-dashed border-divider-deep',
        'bg-transparent transition-all duration-200',
        'hover:border-text-accent hover:bg-state-base-hover hover:shadow-md hover:shadow-shadow-shadow-5',
      )}
    >
      <Link
        href="/datasets/create"
        className="flex min-h-0 grow flex-col items-center justify-center gap-1 px-4 pb-14 pt-4 text-center outline-none"
        data-disable-nprogress={true}
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-state-accent-hover text-text-accent transition-colors group-hover:bg-text-accent group-hover:text-primary-on-surface">
          <RiAddLine className="h-6 w-6" aria-hidden />
        </div>
        <span className="system-md-semibold text-text-secondary group-hover:text-text-primary">
          {t('createDataset', { ns: 'dataset' })}
        </span>
        <span className="system-xs-regular max-w-[220px] text-text-tertiary">
          {t('createKnowledgeCardSubtitle', { ns: 'dataset' })}
        </span>
      </Link>
      <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-2 px-3">
        <Link
          href="/datasets/create-from-pipeline"
          className={cn(
            'system-xs-medium rounded-full border border-divider-regular bg-components-input-bg-normal px-2.5 py-1 text-text-secondary',
            'transition-colors hover:border-text-accent hover:text-text-accent',
          )}
          data-disable-nprogress={true}
        >
          {t('cornerLabel.pipeline', { ns: 'dataset' })}
        </Link>
        <Link
          href="/datasets/connect"
          className={cn(
            'system-xs-medium rounded-full border border-divider-regular bg-components-input-bg-normal px-2.5 py-1 text-text-secondary',
            'transition-colors hover:border-text-accent hover:text-text-accent',
          )}
          data-disable-nprogress={true}
        >
          {t('externalTag', { ns: 'dataset' })}
        </Link>
      </div>
    </div>
  )
}

NewDatasetCard.displayName = 'NewDatasetCard'

export default NewDatasetCard
