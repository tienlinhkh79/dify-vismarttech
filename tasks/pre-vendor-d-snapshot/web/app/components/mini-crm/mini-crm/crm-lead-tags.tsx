'use client'

import Tag from '@/app/components/base/tag'

type CrmLeadTagsProps = {
  tags?: string[] | null
  className?: string
}

const TAG_COLORS = ['green', 'yellow', 'gray', 'red'] as const

export function CrmLeadTags({ tags, className }: CrmLeadTagsProps) {
  if (!tags?.length)
    return null

  return (
    <div className={`flex flex-wrap gap-1 ${className || ''}`}>
      {tags.map((tag, index) => (
        <Tag key={tag} color={TAG_COLORS[index % TAG_COLORS.length]}>
          {tag}
        </Tag>
      ))}
    </div>
  )
}
