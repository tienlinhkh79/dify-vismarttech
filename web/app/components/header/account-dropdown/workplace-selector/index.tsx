import type { Plan } from '@/app/components/billing/type'
import { Menu, MenuButton, MenuItems, Transition } from '@headlessui/react'
import { RiArrowDownSLine } from '@remixicon/react'
import { Fragment } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from '@/app/components/base/ui/toast'
import PlanBadge from '@/app/components/header/plan-badge'
import { useWorkspacesContext } from '@/context/workspace-context'
import { useProviderContext } from '@/context/provider-context'
import { switchWorkspace } from '@/service/common'
import { cn } from '@/utils/classnames'
import { useConsoleNavLayout } from '../../console-nav-layout-context'
import { basePath } from '@/utils/var'

const WorkplaceSelector = ({ tone = 'default' }: { tone?: 'default' | 'onPrimary' }) => {
  const { t } = useTranslation()
  const isOnPrimary = tone === 'onPrimary'
  const { orientation } = useConsoleNavLayout()
  const isSidebar = orientation === 'vertical'
  const { workspaces } = useWorkspacesContext()
  const { enableBilling } = useProviderContext()
  const currentWorkspace = workspaces.find(v => v.current)
  const handleSwitchWorkspace = async (tenant_id: string) => {
    try {
      if (currentWorkspace?.id === tenant_id)
        return
      await switchWorkspace({ url: '/workspaces/switch', body: { tenant_id } })
      toast.success(t('actionMsg.modifiedSuccessfully', { ns: 'common' }))
      location.assign(`${location.origin}${basePath}`)
    }
    catch {
      toast.error(t('provider.saveFailed', { ns: 'common' }))
    }
  }
  return (
    <Menu as="div" className="min-w-0">
      {({ open }) => (
        <>
          <MenuButton
            className={cn(
              'group flex w-full cursor-pointer rounded-[10px] p-0.5',
              isOnPrimary ? 'hover:bg-white/10' : 'hover:bg-state-base-hover',
              open && (isOnPrimary ? 'bg-white/10' : 'bg-state-base-hover'),
              isSidebar && 'items-start gap-2 rounded-xl py-1.5',
              !isSidebar && 'items-center',
            )}
          >
            <div
              className={cn(
                'flex shrink-0 items-center justify-center rounded-md bg-components-icon-bg-blue-solid text-[13px]',
                isSidebar ? 'h-8 w-8' : 'mr-1.5 h-6 w-6 max-[800px]:mr-0',
              )}
            >
              <span className={cn('bg-gradient-to-r from-components-avatar-shape-fill-stop-0 to-components-avatar-shape-fill-stop-100 bg-clip-text align-middle font-semibold uppercase text-shadow-shadow-1 opacity-90', isSidebar ? 'text-sm leading-8' : 'h-6 text-[13px] leading-6')}>{currentWorkspace?.name[0]?.toLocaleUpperCase()}</span>
            </div>
            <div className={cn('flex min-w-0 flex-1', isSidebar ? 'items-start gap-1' : 'items-center')}>
              <div
                className={cn(
                  'min-w-0 text-text-secondary system-sm-medium',
                  isOnPrimary && 'text-white/90',
                  isSidebar
                    ? 'line-clamp-2 flex-1 break-words text-left leading-snug'
                    : 'max-w-[149px] truncate max-[800px]:hidden',
                )}
                title={currentWorkspace?.name}
              >
                {currentWorkspace?.name}
              </div>
              <RiArrowDownSLine
                className={cn(
                  'h-4 w-4 shrink-0',
                  isOnPrimary ? 'text-white/70' : 'text-text-tertiary',
                  isSidebar ? 'mt-0.5' : !isOnPrimary && 'text-text-secondary',
                )}
              />
            </div>
          </MenuButton>
          <Transition as={Fragment} enter="transition ease-out duration-100" enterFrom="transform opacity-0 scale-95" enterTo="transform opacity-100 scale-100" leave="transition ease-in duration-75" leaveFrom="transform opacity-100 scale-100" leaveTo="transform opacity-0 scale-95">
            <MenuItems
              anchor="bottom start"
              className={cn(`
                    shadows-shadow-lg absolute left-[-15px] z-[1000] mt-1 flex max-h-[400px] w-[280px] flex-col items-start overflow-y-auto
                    rounded-xl bg-components-panel-bg-blur backdrop-blur-[5px]
                  `)}
            >
              <div
                className="flex w-full flex-col items-start self-stretch rounded-xl border-[0.5px] border-components-panel-border p-1 pb-2 shadow-lg"
                role="listbox"
                aria-label={t('userProfile.workspace', { ns: 'common' })}
              >
                {workspaces.map(workspace => (
                  <div className="flex items-center gap-2 self-stretch rounded-lg py-1 pl-3 pr-2 hover:bg-state-base-hover" key={workspace.id} onClick={() => handleSwitchWorkspace(workspace.id)}>
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-components-icon-bg-blue-solid text-[13px]">
                      <span className="h-6 bg-gradient-to-r from-components-avatar-shape-fill-stop-0 to-components-avatar-shape-fill-stop-100 bg-clip-text align-middle font-semibold uppercase leading-6 text-shadow-shadow-1 opacity-90">{workspace?.name[0]?.toLocaleUpperCase()}</span>
                    </div>
                    <div className="line-clamp-1 grow cursor-pointer overflow-hidden text-ellipsis text-text-secondary system-md-regular">{workspace.name}</div>
                    {(!enableBilling || workspace.id !== currentWorkspace?.id) && (
                      <PlanBadge plan={workspace.plan as Plan} />
                    )}
                  </div>
                ))}
              </div>
            </MenuItems>
          </Transition>
        </>
      )}
    </Menu>
  )
}
export default WorkplaceSelector
