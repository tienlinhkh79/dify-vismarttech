'use client'

import type { ReactNode } from 'react'
import { createContext, useContext } from 'react'

export type ConsoleNavOrientation = 'horizontal' | 'vertical'

type ConsoleNavLayoutValue = {
  orientation: ConsoleNavOrientation
}

const ConsoleNavLayoutContext = createContext<ConsoleNavLayoutValue>({
  orientation: 'horizontal',
})

export function ConsoleNavLayoutProvider({
  orientation,
  children,
}: {
  orientation: ConsoleNavOrientation
  children: ReactNode
}) {
  return (
    <ConsoleNavLayoutContext.Provider value={{ orientation }}>
      {children}
    </ConsoleNavLayoutContext.Provider>
  )
}

export function useConsoleNavLayout() {
  return useContext(ConsoleNavLayoutContext)
}
