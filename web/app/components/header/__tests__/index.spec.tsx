import { fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import ConsoleChrome from '../index'

function createMockComponent(testId: string) {
  return () => <div data-testid={testId} />
}

vi.mock('@/app/components/header/account-dropdown/workplace-selector', () => ({
  default: createMockComponent('workplace-selector'),
}))

vi.mock('../console-hero-menu', () => ({
  default: function MockConsoleHeroMenu() {
    const { useProviderContext } = require('@/context/provider-context') as typeof import('@/context/provider-context')
    const { useModalContext } = require('@/context/modal-context') as typeof import('@/context/modal-context')
    const { Plan } = require('@/app/components/billing/type') as typeof import('@/app/components/billing/type')
    const { ACCOUNT_SETTING_TAB } = require('@/app/components/header/account-setting/constants') as typeof import('@/app/components/header/account-setting/constants')
    const { enableBilling, plan } = useProviderContext()
    const { setShowPricingModal, setShowAccountSettingModal } = useModalContext()
    return (
      <div data-testid="console-hero-menu">
        <div data-testid="workplace-selector" />
        {enableBilling
          ? (
              <button
                type="button"
                data-testid="plan-badge"
                onClick={() =>
                  plan.type === Plan.sandbox
                    ? setShowPricingModal()
                    : setShowAccountSettingModal({ payload: ACCOUNT_SETTING_TAB.BILLING })}
              />
            )
          : <div data-testid="license-nav" />}
        <div data-testid="plugins-nav" />
        <div data-testid="account-dropdown" />
      </div>
    )
  },
}))

vi.mock('@/app/components/header/account-dropdown', () => ({
  default: createMockComponent('account-dropdown'),
}))

vi.mock('@/app/components/header/app-nav', () => ({
  default: createMockComponent('app-nav'),
}))

vi.mock('@/app/components/header/dataset-nav', () => ({
  default: createMockComponent('dataset-nav'),
}))

vi.mock('@/app/components/header/env-nav', () => ({
  default: createMockComponent('env-nav'),
}))

vi.mock('@/app/components/header/explore-nav', () => ({
  default: createMockComponent('explore-nav'),
}))

vi.mock('@/app/components/header/license-env', () => ({
  default: createMockComponent('license-nav'),
}))

vi.mock('@/app/components/header/plugins-nav', () => ({
  default: createMockComponent('plugins-nav'),
}))

vi.mock('@/app/components/header/tools-nav', () => ({
  default: createMockComponent('tools-nav'),
}))

vi.mock('@/app/components/header/plan-badge', () => ({
  default: ({ onClick, plan }: { onClick?: () => void, plan?: string }) => (
    <button data-testid="plan-badge" onClick={onClick} data-plan={plan} />
  ),
}))

vi.mock('@/context/workspace-context-provider', () => ({
  WorkspaceProvider: ({ children }: { children?: React.ReactNode }) => children,
}))

vi.mock('@/next/link', () => ({
  default: ({ children, href }: { children?: React.ReactNode, href?: string }) => <a href={href}>{children}</a>,
}))

let mockIsWorkspaceEditor = false
let mockIsDatasetOperator = false
let mockMedia = 'desktop'
let mockEnableBilling = false
let mockPlanType = 'sandbox'
let mockBrandingEnabled = false
let mockBrandingTitle: string | null = null
let mockBrandingLogo: string | null = null
const mockSetShowPricingModal = vi.fn()
const mockSetShowAccountSettingModal = vi.fn()

vi.mock('@/context/app-context', () => ({
  useAppContext: () => ({
    isCurrentWorkspaceEditor: mockIsWorkspaceEditor,
    isCurrentWorkspaceDatasetOperator: mockIsDatasetOperator,
    langGeniusVersionInfo: {
      current_version: '0.0.0',
      latest_version: '0.0.0',
      version: '0.0.0',
      release_date: '',
      release_notes: '',
      can_auto_update: false,
      current_env: 'PRODUCTION',
    },
  }),
}))

vi.mock('@/hooks/use-breakpoints', () => ({
  default: () => mockMedia,
  MediaType: { mobile: 'mobile', tablet: 'tablet', desktop: 'desktop' },
}))

vi.mock('@/context/provider-context', () => ({
  useProviderContext: () => ({
    enableBilling: mockEnableBilling,
    plan: { type: mockPlanType },
  }),
}))

vi.mock('@/context/modal-context', () => ({
  useModalContext: () => ({
    setShowPricingModal: mockSetShowPricingModal,
    setShowAccountSettingModal: mockSetShowAccountSettingModal,
  }),
}))

vi.mock('@/context/global-public-context', () => {
  type SystemFeatures = { branding: { enabled: boolean, application_title: string | null, workspace_logo: string | null } }
  return {
    useGlobalPublicStore: (selector: (s: { systemFeatures: SystemFeatures }) => SystemFeatures) =>
      selector({
        systemFeatures: {
          branding: {
            enabled: mockBrandingEnabled,
            application_title: mockBrandingTitle,
            workspace_logo: mockBrandingLogo,
          },
        },
      }),
  }
})

describe('ConsoleChrome', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsWorkspaceEditor = false
    mockIsDatasetOperator = false
    mockMedia = 'desktop'
    mockEnableBilling = false
    mockPlanType = 'sandbox'
    mockBrandingEnabled = false
    mockBrandingTitle = null
    mockBrandingLogo = null
  })

  it('should render header with main nav components', () => {
    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.getByRole('img', { name: /dify logo/i })).toBeInTheDocument()
    expect(screen.getByTestId('console-hero-menu')).toBeInTheDocument()
    expect(screen.getByTestId('workplace-selector')).toBeInTheDocument()
    expect(screen.getByTestId('app-nav')).toBeInTheDocument()
    expect(screen.getByTestId('account-dropdown')).toBeInTheDocument()
  })

  it('should show license nav when billing disabled, plan badge when enabled', () => {
    mockEnableBilling = false
    const { rerender } = render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)
    expect(screen.getByTestId('license-nav')).toBeInTheDocument()
    expect(screen.queryByTestId('plan-badge')).not.toBeInTheDocument()

    mockEnableBilling = true
    rerender(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)
    expect(screen.queryByTestId('license-nav')).not.toBeInTheDocument()
    expect(screen.getByTestId('plan-badge')).toBeInTheDocument()
  })

  it('should hide explore nav when user is dataset operator', () => {
    mockIsDatasetOperator = true
    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.queryByTestId('explore-nav')).not.toBeInTheDocument()
    expect(screen.getByTestId('dataset-nav')).toBeInTheDocument()
  })

  it('should call pricing modal for free plan, settings modal for paid plan', () => {
    mockEnableBilling = true
    mockPlanType = 'sandbox'
    const { rerender } = render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    fireEvent.click(screen.getByTestId('plan-badge'))
    expect(mockSetShowPricingModal).toHaveBeenCalledTimes(1)

    mockPlanType = 'professional'
    rerender(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)
    fireEvent.click(screen.getByTestId('plan-badge'))
    expect(mockSetShowAccountSettingModal).toHaveBeenCalledTimes(1)
  })

  it('should render mobile layout without env nav', () => {
    mockMedia = 'mobile'
    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.getByRole('img', { name: /dify logo/i })).toBeInTheDocument()
    expect(screen.queryByTestId('env-nav')).not.toBeInTheDocument()
  })

  it('should render branded title and repo product logo when branding is enabled', () => {
    mockBrandingEnabled = true
    mockBrandingTitle = 'Acme Workspace'
    mockBrandingLogo = '/logo.png'

    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.getByText('Acme Workspace')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /dify logo/i })).toBeInTheDocument()
  })

  it('should show default Vismarttech logo when branding is enabled but no workspace_logo', () => {
    mockBrandingEnabled = true
    mockBrandingTitle = 'Custom Title'
    mockBrandingLogo = null

    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.getByText('Custom Title')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /dify logo/i })).toBeInTheDocument()
  })

  it('should show default Vismarttech text when branding enabled but no application_title', () => {
    mockBrandingEnabled = true
    mockBrandingTitle = null
    mockBrandingLogo = null

    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.getByText('Vismarttech')).toBeInTheDocument()
  })

  it('should show dataset nav for editor who is not dataset operator', () => {
    mockIsWorkspaceEditor = true
    mockIsDatasetOperator = false

    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.getByTestId('dataset-nav')).toBeInTheDocument()
    expect(screen.getByTestId('explore-nav')).toBeInTheDocument()
    expect(screen.getByTestId('app-nav')).toBeInTheDocument()
  })

  it('should hide dataset nav when neither editor nor dataset operator', () => {
    mockIsWorkspaceEditor = false
    mockIsDatasetOperator = false

    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.queryByTestId('dataset-nav')).not.toBeInTheDocument()
  })

  it('should render mobile layout with dataset operator nav restrictions', () => {
    mockMedia = 'mobile'
    mockIsDatasetOperator = true

    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.queryByTestId('explore-nav')).not.toBeInTheDocument()
    expect(screen.queryByTestId('app-nav')).not.toBeInTheDocument()
    expect(screen.queryByTestId('tools-nav')).not.toBeInTheDocument()
    expect(screen.getByTestId('dataset-nav')).toBeInTheDocument()
  })

  it('should render mobile layout with billing enabled', () => {
    mockMedia = 'mobile'
    mockEnableBilling = true
    mockPlanType = 'sandbox'

    render(<ConsoleChrome><div data-testid="main" /></ConsoleChrome>)

    expect(screen.getByTestId('plan-badge')).toBeInTheDocument()
    expect(screen.queryByTestId('license-nav')).not.toBeInTheDocument()
  })
})
