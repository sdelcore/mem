import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ContentViewer from './ContentViewer'

// Create a wrapper with QueryClientProvider for tests
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('ContentViewer', () => {
  const mockData = [
    {
      id: '1',
      timestamp: '2024-01-15T10:00:00',
      frame: { url: 'http://example.com/frame1.jpg', hash: 'hash123' },
      transcript: 'First transcript',
      annotations: [
        { content: 'Annotation 1', annotation_type: 'note' },
        { content: 'Annotation 2', annotation_type: 'note' },
      ],
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
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={[]} />, { wrapper: createWrapper() })
    expect(screen.getByText('No content in this time range')).toBeInTheDocument()
  })

  it('displays time chunks for time range', () => {
    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        endTime={new Date('2024-01-15T10:02:00')}
        data={mockData}
      />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByText('10:00 - 10:30')).toBeInTheDocument()
    expect(screen.getByText(/time period/)).toBeInTheDocument()
    expect(screen.getByText(/total items/)).toBeInTheDocument()
  })

  it('shows Expand All and Collapse All buttons', () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })
    expect(screen.getByText('Expand All')).toBeInTheDocument()
    expect(screen.getByText('Collapse All')).toBeInTheDocument()
  })

  it('expands chunk when clicking header', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    const chunkContent = document.querySelector('[id^="chunk-content"]')
    expect(chunkContent).toHaveClass('opacity-0')

    fireEvent.click(screen.getByText('10:00 - 10:30'))

    await waitFor(() => {
      expect(chunkContent).toHaveClass('opacity-100')
    })
  })

  it('displays frame with image when chunk is expanded', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('10:00 - 10:30'))

    await waitFor(() => {
      const img = screen.getByAltText('Frame at 10:00:00')
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute('src', 'http://example.com/frame1.jpg')
    })
  })

  it('displays transcript text when chunk is expanded', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('10:00 - 10:30'))

    await waitFor(() => {
      expect(screen.getByText('First transcript')).toBeInTheDocument()
      expect(screen.getByText('Second transcript')).toBeInTheDocument()
    })
  })

  it('displays annotations when chunk is expanded', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('10:00 - 10:30'))

    await waitFor(() => {
      expect(screen.getByText('Annotation 1')).toBeInTheDocument()
      expect(screen.getByText('Annotation 2')).toBeInTheDocument()
    })
  })

  it('collapses chunk when clicking header again', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    const chunkHeader = screen.getByText('10:00 - 10:30')

    fireEvent.click(chunkHeader)
    await waitFor(() => {
      expect(screen.getByText('First transcript')).toBeInTheDocument()
    })

    fireEvent.click(chunkHeader)
    await waitFor(() => {
      const chunkContent = screen.getByText('First transcript').closest('[id^="chunk-content"]')
      expect(chunkContent).toHaveClass('opacity-0')
    })
  })

  it('expands all chunks when clicking Expand All', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('Expand All'))

    await waitFor(() => {
      expect(screen.getByText('First transcript')).toBeInTheDocument()
    })
  })

  it('collapses all chunks when clicking Collapse All', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('Expand All'))
    await waitFor(() => {
      expect(screen.getByText('First transcript')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Collapse All'))
    await waitFor(() => {
      const chunkContent = screen.getByText('First transcript').closest('[id^="chunk-content"]')
      expect(chunkContent).toHaveClass('opacity-0')
    })
  })

  it('shows content type indicators in chunk header', () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })
    const indicators = screen.getAllByTitle(/Has/)
    expect(indicators.length).toBeGreaterThan(0)
  })

  it('filters data to time range correctly', () => {
    const dataWithOutOfRange = [
      ...mockData,
      { id: '4', timestamp: '2024-01-15T11:00:00', transcript: 'Out of range' },
    ]

    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        endTime={new Date('2024-01-15T10:02:00')}
        data={dataWithOutOfRange}
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByText(/1 time period/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('10:00 - 10:30'))
    expect(screen.queryByText('Out of range')).not.toBeInTheDocument()
  })

  it('opens fullscreen modal when clicking on image', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('10:00 - 10:30'))
    await waitFor(() => {
      expect(screen.getByAltText('Frame at 10:00:00')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByAltText('Frame at 10:00:00'))

    await waitFor(() => {
      expect(screen.getByText(/Press ESC or click outside to close/)).toBeInTheDocument()
    })

    // Fullscreen modal has the image with specific classes
    const modal = screen.getByText(/Press ESC/).closest('.fixed')
    expect(modal?.querySelector('img.max-w-full')).toBeInTheDocument()
  })

  it('closes fullscreen modal when clicking close button', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('10:00 - 10:30'))
    await waitFor(() => {
      expect(screen.getByAltText('Frame at 10:00:00')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByAltText('Frame at 10:00:00'))
    await waitFor(() => {
      expect(screen.getByText(/Press ESC or click outside to close/)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByLabelText('Close fullscreen'))

    await waitFor(() => {
      expect(screen.queryByText(/Press ESC or click outside to close/)).not.toBeInTheDocument()
    })
  })

  it('closes fullscreen modal when pressing ESC key', async () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText('10:00 - 10:30'))
    await waitFor(() => {
      expect(screen.getByAltText('Frame at 10:00:00')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByAltText('Frame at 10:00:00'))
    await waitFor(() => {
      expect(screen.getByText(/Press ESC or click outside to close/)).toBeInTheDocument()
    })

    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByText(/Press ESC or click outside to close/)).not.toBeInTheDocument()
    })
  })

  it('groups items into 30-minute chunks', () => {
    const dataAcrossChunks = [
      { id: '1', timestamp: '2024-01-15T10:00:00', transcript: 'Chunk 1 item' },
      { id: '2', timestamp: '2024-01-15T10:35:00', transcript: 'Chunk 2 item' },
    ]

    render(
      <ContentViewer
        startTime={new Date('2024-01-15T10:00:00')}
        endTime={new Date('2024-01-15T11:00:00')}
        data={dataAcrossChunks}
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByText(/2 time periods/)).toBeInTheDocument()
    expect(screen.getByText('10:00 - 10:30')).toBeInTheDocument()
    expect(screen.getByText('10:30 - 11:00')).toBeInTheDocument()
  })

  it('has accessible aria attributes on chunk headers', () => {
    render(<ContentViewer startTime={new Date('2024-01-15T10:00:00')} data={mockData} />, { wrapper: createWrapper() })

    const chunkButton = screen.getByRole('button', { name: /10:00 - 10:30/ })
    expect(chunkButton).toHaveAttribute('aria-expanded', 'false')
    expect(chunkButton).toHaveAttribute('aria-controls')
  })
})
