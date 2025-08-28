import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Sidebar from './Sidebar'

// Mock the child components
vi.mock('./DateSelector', () => ({
  default: ({ selectedDate }: any) => (
    <div data-testid="date-selector">
      Date: {selectedDate.toISOString()}
    </div>
  ),
}))

vi.mock('./VerticalActivityTimeline', () => ({
  default: ({ selectedDate }: any) => (
    <div data-testid="vertical-timeline">
      Timeline for {selectedDate.toISOString()}
    </div>
  ),
}))

describe('Sidebar', () => {
  const defaultProps = {
    selectedDate: new Date('2024-01-15'),
    onDateChange: vi.fn(),
    onTimeSelect: vi.fn(),
    data: [],
  }

  it('renders sidebar with all components', () => {
    render(<Sidebar {...defaultProps} />)
    
    expect(screen.getByTestId('date-selector')).toBeInTheDocument()
    expect(screen.getByTestId('vertical-timeline')).toBeInTheDocument()
    expect(screen.getByText('24-Hour Activity View')).toBeInTheDocument()
  })

  it('renders footer instructions', () => {
    render(<Sidebar {...defaultProps} />)
    
    expect(screen.getByText('Click to navigate • Drag to select')).toBeInTheDocument()
  })

  it('passes props to child components', () => {
    const onDateChange = vi.fn()
    const onTimeSelect = vi.fn()
    
    render(
      <Sidebar
        {...defaultProps}
        onDateChange={onDateChange}
        onTimeSelect={onTimeSelect}
      />
    )
    
    expect(screen.getByTestId('date-selector')).toBeInTheDocument()
    expect(screen.getByTestId('vertical-timeline')).toBeInTheDocument()
  })
})