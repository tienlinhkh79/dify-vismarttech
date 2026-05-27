import type { DataSet } from '@/models/datasets'
import * as React from 'react'
import { cn } from '@/utils/classnames'

type DescriptionProps = {
  dataset: DataSet
}

const Description = ({ dataset }: DescriptionProps) => (
  <div
    className={cn('line-clamp-2 h-10 px-4 py-1 system-xs-regular text-text-tertiary', !dataset.embedding_available && 'opacity-30')}
    title={dataset.description}
  >
    {dataset.description}
  </div>
)

export default React.memo(Description)
