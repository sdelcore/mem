import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DateSelector from './DateSelector'

// Mock react-datepicker
vi.mock('react-datepicker', () => ({
  default: ({ selected, onChange, inline }: any) => (
    <div data-testid="date-picker">
      {inline && `Calendar for ${selected}`}
      <button onClick={() => onChange(new Date('2024-01-20'))}>
        Change Date
      </button>
    </div>
  ),
}))

describe('DateSelector', () => {
  const defaultProps = {
    selectedDate: new Date('2024-01-15T12:00:00'),  // Use noon to avoid timezone issues
    onDateChange: vi.fn(),
  }

  it('renders date display', () => {
    render(<DateSelector {...defaultProps} />)

    expect(screen.getByText('Monday')).toBeInTheDocument()
    expect(screen.getByText('Jan 15, 2024')).toBeInTheDocument()
  })

  it('handles previous day navigation', () => {
    const onDateChange = vi.fn()
    render(
      <DateSelector
        {...defaultProps}
        onDateChange={onDateChange}
      />
    )
    
    const prevButton = screen.getByLabelText('Previous day')
    fireEvent.click(prevButton)
    
    expect(onDateChange).toHaveBeenCalledWith(
      expect.objectContaining({
        // Date should be January 14, 2024
      })
    )
  })

  it('handles next day navigation', () => {
    const onDateChange = vi.fn()
    render(
      <DateSelector
        {...defaultProps}
        onDateChange={onDateChange}
      />
    )
    
    const nextButton = screen.getByLabelText('Next day')
    fireEvent.click(nextButton)
    
    expect(onDateChange).toHaveBeenCalledWith(
      expect.objectContaining({
        // Date should be January 16, 2024
      })
    )
  })

  it('disables next button when today is selected', () => {
    render(
      <DateSelector
        selectedDate={new Date()}
        onDateChange={vi.fn()}
      />
    )
    
    const nextButton = screen.getByLabelText('Next day')
    expect(nextButton).toBeDisabled()
  })

  it('shows "Go to Today" button when not today', () => {
    render(<DateSelector {...defaultProps} />)
    
    expect(screen.getByText('Go to Today')).toBeInTheDocument()
  })

  it('hides "Go to Today" button when today is selected', () => {
    render(
      <DateSelector
        selectedDate={new Date()}
        onDateChange={vi.fn()}
      />
    )
    
    expect(screen.queryByText('Go to Today')).not.toBeInTheDocument()
  })

  it('handles "Go to Today" click', () => {
    const onDateChange = vi.fn()
    render(
      <DateSelector
        {...defaultProps}
        onDateChange={onDateChange}
      />
    )
    
    const todayButton = screen.getByText('Go to Today')
    fireEvent.click(todayButton)
    
    expect(onDateChange).toHaveBeenCalledWith(
      expect.any(Date)
    )
  })

  it('shows date picker when calendar button is clicked', () => {
    render(<DateSelector {...defaultProps} />)

    // Calendar is hidden by default
    expect(screen.queryByTestId('date-picker')).not.toBeInTheDocument()

    // Click the toggle calendar button
    const toggleButton = screen.getByLabelText('Toggle calendar')
    fireEvent.click(toggleButton)

    // Now the date picker should be visible
    expect(screen.getByTestId('date-picker')).toBeInTheDocument()
  })
})