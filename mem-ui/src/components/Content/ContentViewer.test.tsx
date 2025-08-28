import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ContentViewer from './ContentViewer'

describe('ContentViewer', () => {
  const mockData = [
    {
      id: '1',
      timestamp: '2024-01-15T10:00:00',
      frame: { url: 'http://example.com/frame1.jpg', hash: 'hash123' },
      transcript: 'First transcript',
      annotations: ['Annotation 1', 'Annotation 2'],
    },
    {
      id: '2',
      timestamp: '2024-01-15T10:01:00',
      transcript: 'Second transcript',
    },
    {
      id: '3',
      timestamp: '2024-01-15T10:02:00',
      frame: { url: 'http://example.com/frame2.jpg' },
    },
  ]

  it('renders empty state when no data', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={[]}
      />
    )
    
    expect(screen.getByText('No content available for this time range')).toBeInTheDocument()
  })

  it('displays content for time range', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        endTime={new Date('2024-01-15T10:02:00')}
        data={mockData}
      />
    )
    
    expect(screen.getByText('First transcript')).toBeInTheDocument()
    expect(screen.getByText(/Content \d+ of \d+/)).toBeInTheDocument()
  })

  it('displays frame with image', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const img = screen.getByAltText('Frame at 10:00:00')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', 'http://example.com/frame1.jpg')
  })

  it('displays transcript text', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    expect(screen.getByText('First transcript')).toBeInTheDocument()
    // Check for the transcript header specifically
    expect(screen.getByText((content, element) => {
      return element?.className === 'text-sm font-medium text-green-700' && content === 'Transcript'
    })).toBeInTheDocument()
  })

  it('displays annotations list', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    expect(screen.getByText('Annotation 1')).toBeInTheDocument()
    expect(screen.getByText('Annotation 2')).toBeInTheDocument()
    // Check for the annotations header specifically
    expect(screen.getByText((content, element) => {
      return element?.className === 'text-sm font-medium text-orange-700' && content === 'Annotations'
    })).toBeInTheDocument()
  })

  it('navigates between content items', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        endTime={new Date('2024-01-15T10:05:00')}
        data={mockData}
      />
    )
    
    expect(screen.getByText(/Content 1 of \d+/)).toBeInTheDocument()
    expect(screen.getByText('First transcript')).toBeInTheDocument()
    
    // Get all buttons and find the next button (second button)
    const buttons = screen.getAllByRole('button')
    const nextButton = buttons[1] // The next button is the second one
    
    fireEvent.click(nextButton)
    expect(screen.getByText(/Content 2 of \d+/)).toBeInTheDocument()
    expect(screen.getByText('Second transcript')).toBeInTheDocument()
  })

  it('disables previous button at first item', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const buttons = screen.getAllByRole('button')
    const prevButton = buttons[0] as HTMLButtonElement // First button is previous
    
    expect(prevButton).toBeDisabled()
  })

  it('disables next button at last item', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        endTime={new Date('2024-01-15T10:05:00')}
        data={mockData}
      />
    )
    
    const buttons = screen.getAllByRole('button')
    const nextButton = buttons[1] as HTMLButtonElement // Second button is next
    
    // Navigate to last item
    fireEvent.click(nextButton)
    fireEvent.click(nextButton)
    
    expect(screen.getByText(/Content 3 of \d+/)).toBeInTheDocument()
    
    // After navigating, we need to get the buttons again because the component re-rendered
    const buttonsAfterNav = screen.getAllByRole('button')
    const nextButtonAfterNav = buttonsAfterNav[1] as HTMLButtonElement
    expect(nextButtonAfterNav).toBeDisabled()
  })

  it('handles image loading error', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const img = screen.getByAltText('Frame at 10:00:00')
    fireEvent.error(img)
    
    expect(screen.getByText('Failed to load image')).toBeInTheDocument()
  })

  it('shows content type indicators', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    // Check for the color indicators
    const blueIndicator = document.querySelector('.bg-blue-500')
    const greenIndicator = document.querySelector('.bg-green-500')
    const orangeIndicator = document.querySelector('.bg-orange-500')
    
    expect(blueIndicator).toBeInTheDocument()
    expect(greenIndicator).toBeInTheDocument()
    expect(orangeIndicator).toBeInTheDocument()
    
    // Check they are in the indicators section (has specific gap styling)
    const indicatorsSection = document.querySelector('.flex.items-center.gap-4.text-sm.text-gray-600')
    expect(indicatorsSection).toBeInTheDocument()
    expect(indicatorsSection).toContainElement(blueIndicator)
  })

  it('filters data to time range correctly', () => {
    const dataWithOutOfRange = [
      ...mockData,
      {
        id: '4',
        timestamp: '2024-01-15T11:00:00',
        transcript: 'Out of range',
      },
    ]

    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        endTime={new Date('2024-01-15T10:02:00')}
        data={dataWithOutOfRange}
      />
    )
    
    expect(screen.getByText(/Content 1 of \d+/)).toBeInTheDocument()
    expect(screen.queryByText('Out of range')).not.toBeInTheDocument()
  })

  it('opens fullscreen modal when clicking on image', async () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const img = screen.getByAltText('Frame at 10:00:00')
    fireEvent.click(img)
    
    await waitFor(() => {
      expect(screen.getByText('Press ESC or click anywhere to close')).toBeInTheDocument()
    })
    
    // Check if fullscreen image is displayed
    const fullscreenImg = screen.getAllByAltText('Frame at 10:00:00')[1]
    expect(fullscreenImg).toBeInTheDocument()
    expect(fullscreenImg).toHaveClass('max-w-full', 'max-h-[90vh]')
  })

  it('closes fullscreen modal when clicking close button', async () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const img = screen.getByAltText('Frame at 10:00:00')
    fireEvent.click(img)
    
    await waitFor(() => {
      expect(screen.getByText('Press ESC or click anywhere to close')).toBeInTheDocument()
    })
    
    const closeButton = screen.getByLabelText('Close fullscreen')
    fireEvent.click(closeButton)
    
    await waitFor(() => {
      expect(screen.queryByText('Press ESC or click anywhere to close')).not.toBeInTheDocument()
    })
  })

  it('closes fullscreen modal when clicking background', async () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const img = screen.getByAltText('Frame at 10:00:00')
    fireEvent.click(img)
    
    await waitFor(() => {
      expect(screen.getByText('Press ESC or click anywhere to close')).toBeInTheDocument()
    })
    
    // Find and click the overlay background
    const overlay = screen.getByText('Press ESC or click anywhere to close').closest('.fixed')
    if (overlay) {
      fireEvent.click(overlay)
    }
    
    await waitFor(() => {
      expect(screen.queryByText('Press ESC or click anywhere to close')).not.toBeInTheDocument()
    })
  })

  it('closes fullscreen modal when pressing ESC key', async () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const img = screen.getByAltText('Frame at 10:00:00')
    fireEvent.click(img)
    
    await waitFor(() => {
      expect(screen.getByText('Press ESC or click anywhere to close')).toBeInTheDocument()
    })
    
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })
    
    await waitFor(() => {
      expect(screen.queryByText('Press ESC or click anywhere to close')).not.toBeInTheDocument()
    })
  })

  it('does not open fullscreen for failed images', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        data={mockData}
      />
    )
    
    const img = screen.getByAltText('Frame at 10:00:00')
    fireEvent.error(img)
    
    expect(screen.getByText('Failed to load image')).toBeInTheDocument()
    
    // Try to click where the image would be
    const errorContainer = screen.getByText('Failed to load image').parentElement
    if (errorContainer) {
      fireEvent.click(errorContainer)
    }
    
    // Fullscreen modal should not open
    expect(screen.queryByText('Press ESC or click anywhere to close')).not.toBeInTheDocument()
  })
})