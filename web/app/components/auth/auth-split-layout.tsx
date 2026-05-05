'use client'

import type { PropsWithChildren } from 'react'
import { useTranslation } from 'react-i18next'
import Header from '@/app/signin/_header'
import { useGlobalPublicStore } from '@/context/global-public-context'
import useDocumentTitle from '@/hooks/use-document-title'
import { cn } from '@/utils/classnames'
import { showDifyOfficialChrome } from '@/utils/dify-official-chrome'

const AuthSplitLayout = ({ children }: PropsWithChildren) => {
  const { systemFeatures } = useGlobalPublicStore()
  const { t } = useTranslation()
  useDocumentTitle('')

  return (
    <div className={cn('flex min-h-screen w-full bg-background-default-burn p-4 lg:p-5')}>
      <div className="mx-auto flex w-full max-w-[1500px] overflow-hidden rounded-2xl border border-effects-highlight bg-background-default-subtle shadow-xs">
        <div className="flex w-full flex-col lg:w-1/2">
          <div className={cn('flex h-full w-full shrink-0 flex-col items-center bg-background-default-subtle')}>
            <Header />
            <div className={cn('flex w-full grow flex-col items-center justify-center px-6 pb-8 md:px-[88px]')}>
              <div className="flex flex-col md:w-[420px]">
                {children}
              </div>
            </div>
            {showDifyOfficialChrome(systemFeatures.branding.enabled) && (
              <div className="system-xs-regular px-8 py-6 text-text-tertiary">
                ©
                {' '}
                {new Date().getFullYear()}
                {' '}
                LangGenius, Inc. All rights reserved.
              </div>
            )}
          </div>
        </div>

        <div className="relative hidden w-1/2 overflow-hidden border-l border-effects-highlight bg-linear-to-br from-[#2f35dc] via-[#3b44e8] to-[#2c53f1] p-6 lg:block">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(255,255,255,0.15)_0%,rgba(255,255,255,0)_40%),radial-gradient(circle_at_78%_20%,rgba(255,255,255,0.12)_0%,rgba(255,255,255,0)_35%)]" />
          <div className="relative z-10 flex h-full flex-col rounded-2xl border border-white/15 p-10">
            <div className="max-w-[440px] text-white">
              <h2 className="text-4xl font-semibold leading-tight">
                {t('rightTitle', { ns: 'login' })}
              </h2>
              <p className="mt-4 text-base text-white/80">
                {t('rightDesc', { ns: 'login' })}
              </p>
            </div>
            <div className="mt-10 rounded-2xl border border-white/20 bg-white/95 p-5 shadow-2xl">
              <div className="mb-4 flex items-center justify-between text-slate-600">
                <span className="text-xs font-semibold">Sales Overview</span>
                <span className="h-2 w-16 rounded-full bg-blue-200" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-xs text-slate-500">Total Sales</div>
                  <div className="mt-1 text-xl font-bold text-slate-900">$189,374</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-xs text-slate-500">Orders</div>
                  <div className="mt-1 text-xl font-bold text-slate-900">6,248</div>
                </div>
                <div className="col-span-2 rounded-xl bg-slate-50 p-3">
                  <div className="text-xs text-slate-500">Growth</div>
                  <div className="mt-2 h-2 w-full rounded-full bg-slate-200">
                    <div className="h-2 w-2/3 rounded-full bg-blue-500" />
                  </div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2">
                <div className="h-12 rounded-lg bg-slate-100" />
                <div className="h-12 rounded-lg bg-slate-100" />
                <div className="h-12 rounded-lg bg-slate-100" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AuthSplitLayout
