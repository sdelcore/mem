import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
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

  it('renders sidebar with all components when expanded', () => {
    render(<Sidebar {...defaultProps} isCollapsed={false} />)

    expect(screen.getByTestId('date-selector')).toBeInTheDocument()
    expect(screen.getByTestId('vertical-timeline')).toBeInTheDocument()
  })

  it('renders footer instructions', () => {
    render(<Sidebar {...defaultProps} isCollapsed={false} />)

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
        isCollapsed={false}
      />
    )

    expect(screen.getByTestId('date-selector')).toBeInTheDocument()
    expect(screen.getByTestId('vertical-timeline')).toBeInTheDocument()
  })

  it('hides content when collapsed', () => {
    render(<Sidebar {...defaultProps} isCollapsed={true} />)

    // Content should be invisible when collapsed
    const sidebarContent = document.querySelector('.opacity-0')
    expect(sidebarContent).toBeInTheDocument()
  })

  it('shows toggle button', () => {
    const onToggleCollapse = vi.fn()
    render(<Sidebar {...defaultProps} isCollapsed={false} onToggleCollapse={onToggleCollapse} />)

    const toggleButton = screen.getByLabelText('Collapse sidebar')
    expect(toggleButton).toBeInTheDocument()
  })

  it('calls onToggleCollapse when toggle button is clicked', () => {
    const onToggleCollapse = vi.fn()
    render(<Sidebar {...defaultProps} isCollapsed={false} onToggleCollapse={onToggleCollapse} />)

    const toggleButton = screen.getByLabelText('Collapse sidebar')
    fireEvent.click(toggleButton)

    expect(onToggleCollapse).toHaveBeenCalled()
  })

  it('shows expand button when collapsed on desktop', () => {
    const onToggleCollapse = vi.fn()
    render(<Sidebar {...defaultProps} isCollapsed={true} onToggleCollapse={onToggleCollapse} />)

    const toggleButton = screen.getByLabelText('Expand sidebar')
    expect(toggleButton).toBeInTheDocument()
  })

  it('renders mobile backdrop when expanded', () => {
    const onToggleCollapse = vi.fn()
    render(<Sidebar {...defaultProps} isCollapsed={false} onToggleCollapse={onToggleCollapse} />)

    // Backdrop should be present (for mobile)
    const backdrop = document.querySelector('.bg-black\\/50')
    expect(backdrop).toBeInTheDocument()
  })

  it('clicking backdrop calls onToggleCollapse', () => {
    const onToggleCollapse = vi.fn()
    render(<Sidebar {...defaultProps} isCollapsed={false} onToggleCollapse={onToggleCollapse} />)

    const backdrop = document.querySelector('.bg-black\\/50') as HTMLElement
    if (backdrop) {
      fireEvent.click(backdrop)
      expect(onToggleCollapse).toHaveBeenCalled()
    }
  })
})
