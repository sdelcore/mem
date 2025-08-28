import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VerticalActivityTimeline from './VerticalActivityTimeline'

describe('VerticalActivityTimeline', () => {
  const defaultProps = {
    selectedDate: new Date('2024-01-15'),
    onTimeSelect: vi.fn(),
    data: [],
  }

  it('renders all 24 hours', () => {
    render(<VerticalActivityTimeline {...defaultProps} />)
    
    expect(screen.getByText('00:00')).toBeInTheDocument()
    expect(screen.getByText('12:00')).toBeInTheDocument()
    expect(screen.getByText('23:00')).toBeInTheDocument()
  })

  it('handles hour click', () => {
    const onTimeSelect = vi.fn()
    render(
      <VerticalActivityTimeline
        {...defaultProps}
        onTimeSelect={onTimeSelect}
      />
    )
    
    const hour12 = screen.getByText('12:00').parentElement
    if (hour12) {
      fireEvent.click(hour12)
      expect(onTimeSelect).toHaveBeenCalledWith(expect.any(Date))
    }
  })

  it('displays activity data', () => {
    const data = [
      {
        timestamp: new Date('2024-01-15T10:30:00'),
        frame: { url: 'test.jpg' },
      },
      {
        timestamp: new Date('2024-01-15T10:45:00'),
        transcript: 'test',
      },
    ]

    render(
      <VerticalActivityTimeline
        {...defaultProps}
        data={data}
      />
    )
    
    // Should show count for hour 10
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows current time marker for today', () => {
    const today = new Date()
    const { container } = render(
      <VerticalActivityTimeline
        {...defaultProps}
        selectedDate={today}
        currentTime={today}
      />
    )
    
    // Should have a red marker line
    const marker = container.querySelector('.bg-red-500')
    expect(marker).toBeInTheDocument()
  })

  it('handles range selection', () => {
    const onRangeSelect = vi.fn()
    render(
      <VerticalActivityTimeline
        {...defaultProps}
        onRangeSelect={onRangeSelect}
      />
    )
    
    const hour10 = screen.getByText('10:00').parentElement
    const hour12 = screen.getByText('12:00').parentElement
    
    if (hour10 && hour12) {
      fireEvent.mouseDown(hour10)
      fireEvent.mouseMove(hour12)
      fireEvent.mouseUp(hour12)
      
      expect(onRangeSelect).toHaveBeenCalledWith(
        expect.any(Date),
        expect.any(Date)
      )
    }
  })

  it('shows hover state', () => {
    render(<VerticalActivityTimeline {...defaultProps} />)
    
    const hour10 = screen.getByText('10:00').parentElement
    
    if (hour10) {
      fireEvent.mouseMove(hour10)
      expect(hour10.className).toContain('bg-forest-500/20')
    }
  })
})