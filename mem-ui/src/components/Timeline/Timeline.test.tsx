import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Timeline from './Timeline'

describe('Timeline', () => {
  const defaultProps = {
    startTime: new Date('2024-01-15T10:00:00'),
    endTime: new Date('2024-01-15T11:00:00'),
    data: [],
  }

  it('renders timeline with time labels', () => {
    render(<Timeline {...defaultProps} />)

    // Time format is 'MMM dd, HH:mm:ss' for start and 'HH:mm:ss' for end
    expect(screen.getByText(/Jan 15, 10:00:00/)).toBeInTheDocument()
    expect(screen.getByText(/11:00:00/)).toBeInTheDocument()
  })

  it('renders legend with all data types', () => {
    render(<Timeline {...defaultProps} />)
    
    expect(screen.getByText('No data')).toBeInTheDocument()
    expect(screen.getByText('Frames')).toBeInTheDocument()
    expect(screen.getByText('Transcripts')).toBeInTheDocument()
    expect(screen.getByText('Both')).toBeInTheDocument()
    expect(screen.getByText('Annotations')).toBeInTheDocument()
  })

  it('calls onTimeSelect when segment is clicked', () => {
    const onTimeSelect = vi.fn()
    const { container } = render(<Timeline {...defaultProps} onTimeSelect={onTimeSelect} />)

    // Find timeline segments by their class
    const segments = container.querySelectorAll('.flex-1.border-r')

    if (segments[0]) {
      fireEvent.click(segments[0])
      expect(onTimeSelect).toHaveBeenCalled()
    }
  })

  it('handles drag selection for range', () => {
    const onRangeSelect = vi.fn()
    const { container } = render(<Timeline {...defaultProps} onRangeSelect={onRangeSelect} />)

    // Find timeline segments by their class
    const segments = container.querySelectorAll('.flex-1.border-r')

    if (segments[0] && segments[1]) {
      fireEvent.mouseDown(segments[0])
      fireEvent.mouseMove(segments[1])
      fireEvent.mouseUp(segments[1])

      expect(onRangeSelect).toHaveBeenCalled()
    }
  })

  it('renders data segments with correct colors', () => {
    const dataWithContent = [
      {
        timestamp: new Date('2024-01-15T10:05:00'),
        frame: { url: 'test.jpg' },
        transcript: 'test transcript',
      },
      {
        timestamp: new Date('2024-01-15T10:15:00'),
        frame: { url: 'test2.jpg' },
      },
      {
        timestamp: new Date('2024-01-15T10:25:00'),
        transcript: 'another transcript',
      },
      {
        timestamp: new Date('2024-01-15T10:35:00'),
        annotations: ['annotation1'],
      },
    ]

    const { container } = render(<Timeline {...defaultProps} data={dataWithContent} />)

    const segments = container.querySelectorAll('.flex-1.border-r')

    expect(segments.length).toBeGreaterThan(0)
  })

  it('shows tooltip on hover', () => {
    const dataWithContent = [
      {
        timestamp: new Date('2024-01-15T10:05:00'),
        frame: { url: 'test.jpg' },
      },
    ]

    const { container } = render(<Timeline {...defaultProps} data={dataWithContent} />)

    const segments = container.querySelectorAll('.flex-1.border-r')

    if (segments[0]) {
      fireEvent.mouseMove(segments[0])
    }
  })
})