'use client'

import type { MiniCrmStage } from './constants'
import { useTranslation } from '#i18n'
import Tag from '@/app/components/base/tag'

const STAGE_TAG_COLOR: Record<MiniCrmStage, 'gray' | 'yellow' | 'green' | 'red'> = {
  new: 'gray',
  qualified: 'yellow',
  won: 'green',
  lost: 'red',
}

type StageTagProps = {
  stage: string
  className?: string
}

export function StageTag({ stage, className }: StageTagProps) {
  const { t } = useTranslation('common')
  const stageKey = stage as MiniCrmStage
  const color = STAGE_TAG_COLOR[stageKey] ?? 'gray'
  const labelKey = {
    new: 'miniCrm.stageNew',
    qualified: 'miniCrm.stageQualified',
    won: 'miniCrm.stageWon',
    lost: 'miniCrm.stageLost',
  }[stageKey] as 'miniCrm.stageNew' | 'miniCrm.stageQualified' | 'miniCrm.stageWon' | 'miniCrm.stageLost' | undefined

  return (
    <Tag color={color} className={className}>
      {labelKey ? t(labelKey) : stage}
    </Tag>
  )
}
