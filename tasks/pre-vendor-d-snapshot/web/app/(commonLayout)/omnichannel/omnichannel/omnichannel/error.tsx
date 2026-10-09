'use client'

import Button from '@/app/components/base/button'

export default function OmnichannelError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex min-h-[50vh] flex-1 flex-col items-center justify-center gap-4 p-8">
      <h2 className="text-lg font-semibold text-text-primary">Omnichannel failed to load</h2>
      <p className="max-w-lg text-center text-sm text-text-secondary">{error.message}</p>
      <div className="flex gap-2">
        <Button variant="primary" onClick={() => { reset() }}>Retry</Button>
      </div>
    </div>
  )
}
