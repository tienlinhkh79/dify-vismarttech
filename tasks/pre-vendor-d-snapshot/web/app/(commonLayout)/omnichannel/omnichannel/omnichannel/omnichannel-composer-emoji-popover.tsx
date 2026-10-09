'use client'

import type { FC } from 'react'
import data from '@emoji-mart/data'
import type { EmojiMartData } from '@emoji-mart/data'
import { RiEmotionLine } from '@remixicon/react'
import { useCallback, useMemo, useState } from 'react'
import { useTranslation } from '#i18n'
import ActionButton from '@/app/components/base/action-button'
import Input from '@/app/components/base/input'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/base/ui/popover'
import { cn } from '@/utils/classnames'
import { searchEmoji } from '@/utils/emoji'

type OmnichannelComposerEmojiPopoverProps = {
  disabled?: boolean
  onSelect: (emoji: string) => void
}

const OmnichannelComposerEmojiPopover: FC<OmnichannelComposerEmojiPopoverProps> = ({
  disabled,
  onSelect,
}) => {
  const { t } = useTranslation('common')
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<string[]>([])

  const frequentEmojis = useMemo(() => {
    const categories = (data as EmojiMartData).categories
    const smileys = categories.find(c => c.id === 'smileys_people')
    const symbols = categories.find(c => c.id === 'symbols')
    const ids = [...(smileys?.emojis || []).slice(0, 24), ...(symbols?.emojis || []).slice(0, 8)]
    const emojis = (data as EmojiMartData).emojis
    return ids
      .map(id => emojis[id]?.skins?.[0]?.native)
      .filter((value): value is string => !!value)
  }, [])

  const onSearchChange = useCallback(async (value: string) => {
    setSearch(value)
    if (!value.trim()) {
      setSearchResults([])
      return
    }
    const results = await searchEmoji(value.trim())
    setSearchResults(results.slice(0, 32))
  }, [])

  const displayEmojis = search.trim() ? searchResults : frequentEmojis

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <ActionButton
          type="button"
          size="l"
          disabled={disabled}
          aria-label={t('settings.omnichannelComposerEmoji')}
          className={cn(open && 'action-btn-active')}
        >
          <RiEmotionLine className="h-5 w-5" />
        </ActionButton>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-2">
        <Input
          value={search}
          onChange={e => void onSearchChange(e.target.value)}
          placeholder={t('settings.omnichannelComposerEmojiSearch')}
          className="mb-2"
        />
        <div className="grid max-h-48 grid-cols-8 gap-0.5 overflow-y-auto">
          {displayEmojis.map(emoji => (
            <button
              key={emoji}
              type="button"
              className="rounded p-1 text-lg hover:bg-state-base-hover"
              onClick={() => {
                onSelect(emoji)
                setOpen(false)
                setSearch('')
                setSearchResults([])
              }}
            >
              {emoji}
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  )
}

export default OmnichannelComposerEmojiPopover
