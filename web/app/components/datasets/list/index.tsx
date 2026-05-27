'use client'

import { RiSearchLine } from '@remixicon/react'
import { useBoolean, useDebounceFn } from 'ahooks'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'

import Button from '@/app/components/base/button'
import { ApiConnectionMod } from '@/app/components/base/icons/src/vender/solid/development'
import Input from '@/app/components/base/input'
import TagManagementModal from '@/app/components/base/tag-management'
import TagFilter from '@/app/components/base/tag-management/filter'
import { useStore as useTagStore } from '@/app/components/base/tag-management/store'
import CheckboxWithLabel from '@/app/components/datasets/create/website/base/checkbox-with-label'
import { useAppContext, useSelector as useAppContextSelector } from '@/context/app-context'
import { useExternalApiPanel } from '@/context/external-api-panel-context'
import { useGlobalPublicStore } from '@/context/global-public-context'
import useDocumentTitle from '@/hooks/use-document-title'
import { useDatasetApiBaseUrl } from '@/service/knowledge/use-dataset'
import { cn } from '@/utils/classnames'
import ExternalAPIPanel from '../external-api/external-api-panel'
import ServiceApi from '../extra-info/service-api'
import DatasetFooter from './dataset-footer'
import Datasets from './datasets'

const List = () => {
  const { t } = useTranslation()
  const { t: tApp } = useTranslation('app')
  const { systemFeatures } = useGlobalPublicStore()
  const { isCurrentWorkspaceOwner } = useAppContext()
  const showTagManagementModal = useTagStore(s => s.showTagManagementModal)
  const { showExternalApiPanel, setShowExternalApiPanel } = useExternalApiPanel()
  const [includeAll, { toggle: toggleIncludeAll }] = useBoolean(false)
  useDocumentTitle(t('knowledge', { ns: 'dataset' }))

  const [keywords, setKeywords] = useState('')
  const [searchKeywords, setSearchKeywords] = useState('')
  const { run: handleSearch } = useDebounceFn(() => {
    setSearchKeywords(keywords)
  }, { wait: 500 })
  const handleKeywordsChange = (value: string) => {
    setKeywords(value)
    handleSearch()
  }
  const [tagFilterValue, setTagFilterValue] = useState<string[]>([])
  const [tagIDs, setTagIDs] = useState<string[]>([])
  const { run: handleTagsUpdate } = useDebounceFn(() => {
    setTagIDs(tagFilterValue)
  }, { wait: 500 })
  const handleTagsChange = (value: string[]) => {
    setTagFilterValue(value)
    handleTagsUpdate()
  }

  const isCurrentWorkspaceManager = useAppContextSelector(state => state.isCurrentWorkspaceManager)
  const { data: apiBaseInfo } = useDatasetApiBaseUrl()

  const openCommandPalette = useCallback(() => {
    window.dispatchEvent(new CustomEvent('dify:open-goto-anything'))
  }, [])

  return (
    <div className="scroll-container relative flex grow flex-col overflow-y-auto bg-background-body">
      <div
        className={cn(
          'sticky top-0 z-10 shrink-0 border-b border-divider-regular bg-background-body/90 backdrop-blur-md',
        )}
      >
        <div className="flex flex-col gap-4 px-6 pt-5 pb-4 md:px-12 md:pt-6 md:pb-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-6">
            <div className="min-w-0 shrink-0 lg:max-w-[min(100%,14rem)]">
              <h1 className="text-xl font-semibold tracking-tight text-text-primary md:text-2xl">
                {t('knowledgeStore', { ns: 'dataset' })}
              </h1>
            </div>
            <button
              type="button"
              onClick={openCommandPalette}
              className={cn(
                'flex min-h-10 w-full min-w-0 cursor-pointer items-center gap-2 rounded-xl border border-divider-regular system-sm-regular',
                'bg-components-input-bg-normal px-3 py-2.5 text-left text-text-tertiary transition-colors',
                'hover:border-divider-deep hover:bg-state-base-hover hover:text-text-secondary',
                'lg:mx-auto lg:max-w-2xl lg:flex-1',
              )}
            >
              <RiSearchLine className="h-4 w-4 shrink-0" aria-hidden />
              <span className="min-w-0 flex-1 truncate">{tApp('gotoAnything.searchPlaceholder')}</span>
            </button>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
              {isCurrentWorkspaceOwner && (
                <div
                  className={cn(
                    'inline-flex shrink-0 rounded-xl border border-divider-regular bg-components-input-bg-normal px-1 py-1',
                  )}
                >
                  <CheckboxWithLabel
                    isChecked={includeAll}
                    onChange={toggleIncludeAll}
                    label={t('allKnowledge', { ns: 'dataset' })}
                    labelClassName="system-sm-medium text-text-secondary"
                    className="px-2"
                    tooltip={t('allKnowledgeDescription', { ns: 'dataset' }) as string}
                  />
                </div>
              )}
              <div className="min-w-0 sm:max-w-[220px]">
                <TagFilter type="knowledge" value={tagFilterValue} onChange={handleTagsChange} />
              </div>
              <Input
                showLeftIcon
                showClearIcon
                wrapperClassName="w-full min-w-0 sm:max-w-xs md:max-w-sm lg:max-w-md"
                placeholder={t('listSearchKnowledgePlaceholder', { ns: 'dataset' })}
                value={keywords}
                onChange={e => handleKeywordsChange(e.target.value)}
                onClear={() => handleKeywordsChange('')}
              />
            </div>
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
              {isCurrentWorkspaceManager && (
                <>
                  <ServiceApi apiBaseUrl={apiBaseInfo?.api_base_url ?? ''} />
                  <div className="hidden h-4 w-px bg-divider-regular sm:block" />
                </>
              )}
              <Button
                className="shadows-shadow-xs gap-0.5 rounded-xl"
                onClick={() => setShowExternalApiPanel(true)}
              >
                <ApiConnectionMod className="h-4 w-4 text-components-button-secondary-text" />
                <div className="flex items-center justify-center gap-1 px-0.5 system-sm-medium text-components-button-secondary-text">
                  {t('externalAPIPanelTitle', { ns: 'dataset' })}
                </div>
              </Button>
            </div>
          </div>
        </div>
      </div>
      <Datasets tags={tagIDs} keywords={searchKeywords} includeAll={includeAll} />
      {!systemFeatures.branding.enabled && <DatasetFooter />}
      {showTagManagementModal && (
        <TagManagementModal type="knowledge" show={showTagManagementModal} />
      )}
      {showExternalApiPanel && <ExternalAPIPanel onClose={() => setShowExternalApiPanel(false)} />}
    </div>
  )
}

export default List
