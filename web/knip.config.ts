import type { KnipConfig } from 'knip'

/**
 * @see https://knip.dev/reference/configuration
 */
const config: KnipConfig = {
  entry: [
    'scripts/**/*.{js,ts,mjs}',
    'bin/**/*.{js,ts,mjs}',
    'tsslint.config.ts',
  ],
  ignore: [
    'public/**',
    'app/(commonLayout)/omnichannel/apply-layout.mjs',
    'app/components/base/loading/style.css',
    'app/components/header/account-setting/tools-page.tsx',
    'service/tools.ts',
    'app/components/header/console-nav-sidebar-item-class.ts',
    'app/components/header/console-branded-logo.tsx',
    'app/components/header/account-dropdown/account-menu-panel.tsx',
    'app/components/header/console-nav-layout-context.tsx',
    'app/components/header/account-setting/channel-setup-config.ts',
    'app/components/header/console-hero-menu.tsx',
  ],
  ignoreBinaries: [
    'only-allow',
  ],
  ignoreDependencies: [
    '@iconify-json/*',

    '@storybook/addon-onboarding',

  ],
  /// keep-sorted
  rules: {
    binaries: 'error',
    catalog: 'error',
    dependencies: 'error',
    devDependencies: 'error',
    duplicates: 'error',
    enumMembers: 'error',
    exports: 'error',
    files: 'error',
    namespaceMembers: 'error',
    nsExports: 'error',
    nsTypes: 'error',
    optionalPeerDependencies: 'error',
    types: 'error',
    unlisted: 'error',
    unresolved: 'error',
  },
}

export default config
