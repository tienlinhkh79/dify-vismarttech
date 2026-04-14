'use client'
import useTheme from '@/hooks/use-theme'
import { cn } from '@/utils/classnames'
import { basePath } from '@/utils/var'

export type LogoStyle = 'default' | 'monochromeWhite'

export const logoPathMap: Record<LogoStyle, string> = {
  default: '/logo/logo.png',
  monochromeWhite: '/logo/logo.png',
}

export type LogoSize = 'large' | 'medium' | 'small'

export const logoSizeMap: Record<LogoSize, string> = {
  large: 'h-10 w-10',
  medium: 'h-8 w-8',
  small: 'h-6 w-6',
}

type DifyLogoProps = {
  style?: LogoStyle
  size?: LogoSize
  className?: string
}

const DifyLogo = ({
  style = 'default',
  size = 'medium',
  className,
}: DifyLogoProps) => {
  const { theme } = useTheme()
  const themedStyle = (theme === 'dark' && style === 'default') ? 'monochromeWhite' : style

  return (
    <img
      src={`${basePath}${logoPathMap[themedStyle]}`}
      className={cn('block object-contain', logoSizeMap[size], className)}
      alt="Dify logo"
    />
  )
}

export default DifyLogo
