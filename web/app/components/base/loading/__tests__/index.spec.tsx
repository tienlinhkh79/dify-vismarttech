import { render } from '@testing-library/react'
import * as React from 'react'
import Loading from '../index'

describe('Loading Component', () => {
  it('renders correctly with default props', () => {
    const { container } = render(<Loading />)
    expect(container.firstChild).toHaveClass('flex w-full items-center justify-center')
    expect(container.firstChild).not.toHaveClass('h-full')
  })

  it('renders correctly with area type', () => {
    const { container } = render(<Loading type="area" />)
    expect(container.firstChild).not.toHaveClass('h-full')
  })

  it('renders correctly with app type', () => {
    const { container } = render(<Loading type="app" />)
    expect(container.firstChild).toHaveClass('h-full')
  })

  it('contains loading animation container', () => {
    const { container } = render(<Loading />)
    expect(container.querySelector('.spin-animation')).toBeInTheDocument()
  })

  it('shows logo when using app type', () => {
    const { container } = render(<Loading type="app" />)
    expect(container.querySelector('img')).toBeInTheDocument()
  })

  it('handles undefined props correctly', () => {
    const { container } = render(Loading() as unknown as React.ReactElement)
    expect(container.firstChild).toHaveClass('flex w-full items-center justify-center')
  })
})
