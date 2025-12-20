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
    // Use timestamps that match the selectedDate
    const baseDate = new Date('2024-01-15T00:00:00')
    const data = [
      {
        timestamp: new Date(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate(), 10, 30, 0).toISOString(),
        frame: { url: 'test.jpg' },
      },
      {
        timestamp: new Date(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate(), 10, 45, 0).toISOString(),
        transcript: 'test',
      },
    ]

    const { container } = render(
      <VerticalActivityTimeline
        selectedDate={baseDate}
        onTimeSelect={vi.fn()}
        data={data}
      />
    )

    // Check that hour 10 has activity bar rendered
    const hour10 = container.querySelector('[data-hour="10"]')
    expect(hour10).toBeInTheDocument()

    // There should be an activity bar with some content
    const activityBars = hour10?.querySelectorAll('.rounded')
    expect(activityBars?.length).toBeGreaterThan(0)
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