import type { ReactNode } from 'react'
import { MiniCrmMobileSubNav } from '@/app/components/mini-crm/mini-crm-mobile-sub-nav'

export default function MiniCrmLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex h-0 min-h-0 shrink-0 grow overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <MiniCrmMobileSubNav />
        {children}
      </div>
    </div>
  )
}
