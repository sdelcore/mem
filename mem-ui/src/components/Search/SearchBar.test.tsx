import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SearchBar from './SearchBar'

// Mock fetch
global.fetch = vi.fn()

describe('SearchBar', () => {
  const mockOnSearch = vi.fn()
  const mockOnResultClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders search input with placeholder', () => {
    render(
      <SearchBar
        placeholder="Search transcripts..."
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    expect(screen.getByPlaceholderText('Search transcripts...')).toBeInTheDocument()
  })

  it('shows clear button when text is entered', async () => {
    const user = userEvent.setup({ delay: null })
    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...')
    await user.type(input, 'test query')
    
    const clearButton = screen.getByRole('button')
    expect(clearButton).toBeInTheDocument()
  })

  it('clears search when clear button is clicked', async () => {
    const user = userEvent.setup({ delay: null })
    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...') as HTMLInputElement
    await user.type(input, 'test query')
    
    const clearButton = screen.getByRole('button')
    await user.click(clearButton)
    
    expect(input.value).toBe('')
  })

  it('debounces search calls', async () => {
    const user = userEvent.setup({ delay: null })
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ results: [] }),
    })

    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...')
    await user.type(input, 'test')
    
    // Should not call immediately
    expect(mockOnSearch).not.toHaveBeenCalled()
    
    // Fast-forward debounce timer
    vi.advanceTimersByTime(300)
    
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith('test')
    })
  })

  it('displays search results', async () => {
    const user = userEvent.setup({ delay: null })
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          {
            id: '1',
            timestamp: '2024-01-15T14:30:00',
            text: 'This is a test transcript',
            type: 'transcript',
            highlight: 'test',
          },
          {
            id: '2',
            timestamp: '2024-01-15T14:31:00',
            text: 'Another test annotation',
            type: 'annotation',
            highlight: 'test',
          },
        ],
      }),
    })

    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...')
    await user.type(input, 'test')
    
    vi.advanceTimersByTime(300)
    
    await waitFor(() => {
      expect(screen.getByText(/This is a/)).toBeInTheDocument()
      expect(screen.getByText(/Another/)).toBeInTheDocument()
    })
  })

  it('calls onResultClick when result is clicked', async () => {
    const user = userEvent.setup({ delay: null })
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          {
            id: '1',
            timestamp: '2024-01-15T14:30:00',
            text: 'Test result',
            type: 'transcript',
          },
        ],
      }),
    })

    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...')
    await user.type(input, 'test')
    
    vi.advanceTimersByTime(300)
    
    await waitFor(() => {
      expect(screen.getByText('Test result')).toBeInTheDocument()
    })
    
    await user.click(screen.getByText('Test result'))
    
    expect(mockOnResultClick).toHaveBeenCalledWith(
      expect.any(Date)
    )
  })

  it('shows no results message', async () => {
    const user = userEvent.setup({ delay: null })
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ results: [] }),
    })

    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...')
    await user.type(input, 'nonexistent')
    
    vi.advanceTimersByTime(300)
    
    await waitFor(() => {
      expect(screen.getByText('No results found for "nonexistent"')).toBeInTheDocument()
    })
  })

  it('handles search errors gracefully', async () => {
    const user = userEvent.setup({ delay: null })
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...')
    await user.type(input, 'test')
    
    vi.advanceTimersByTime(300)
    
    // Should handle error without crashing
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith('test')
    })
  })

  it('does not search for queries shorter than 2 characters', async () => {
    const user = userEvent.setup({ delay: null })
    
    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )
    
    const input = screen.getByPlaceholderText('Search...')
    await user.type(input, 'a')
    
    vi.advanceTimersByTime(300)
    
    expect(mockOnSearch).not.toHaveBeenCalled()
  })
})