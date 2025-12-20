import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import SearchBar from './SearchBar'

// Mock fetch
global.fetch = vi.fn()

describe('SearchBar', () => {
  const mockOnSearch = vi.fn()
  const mockOnResultClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockReset()
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
    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )

    const input = screen.getByPlaceholderText('Search...')
    fireEvent.change(input, { target: { value: 'test query' } })

    // Clear button should appear
    const clearButton = screen.getByRole('button')
    expect(clearButton).toBeInTheDocument()
  })

  it('clears search when clear button is clicked', async () => {
    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )

    const input = screen.getByPlaceholderText('Search...') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'test query' } })

    const clearButton = screen.getByRole('button')
    fireEvent.click(clearButton)

    expect(input.value).toBe('')
  })

  it('debounces search calls', async () => {
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
    fireEvent.change(input, { target: { value: 'test' } })

    // Should not call immediately
    expect(mockOnSearch).not.toHaveBeenCalled()

    // Wait for debounce to complete (300ms + buffer)
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith('test')
    }, { timeout: 500 })
  })

  it('displays search results', async () => {
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
    fireEvent.change(input, { target: { value: 'test' } })

    await waitFor(() => {
      expect(screen.getByText(/This is a/)).toBeInTheDocument()
    }, { timeout: 1000 })
  })

  it('calls onResultClick when result is clicked', async () => {
    // Create a fresh mock for this test
    const originalFetch = global.fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
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
    fireEvent.change(input, { target: { value: 'testquery' } })

    // Wait for debounce + fetch + render
    await waitFor(() => {
      expect(screen.getByText('Test result')).toBeInTheDocument()
    }, { timeout: 3000, interval: 50 })

    fireEvent.click(screen.getByText('Test result'))

    expect(mockOnResultClick).toHaveBeenCalledWith(expect.any(Date))

    global.fetch = originalFetch
  })

  it('shows no results message', async () => {
    // Create a fresh mock for this test
    const originalFetch = global.fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: [] }),
    })

    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )

    const input = screen.getByPlaceholderText('Search...')
    fireEvent.change(input, { target: { value: 'nonexistent' } })

    // Wait for debounce + fetch + render
    await waitFor(() => {
      expect(screen.getByText('No results found for "nonexistent"')).toBeInTheDocument()
    }, { timeout: 3000, interval: 50 })

    global.fetch = originalFetch
  })

  it('handles search errors gracefully', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )

    const input = screen.getByPlaceholderText('Search...')
    fireEvent.change(input, { target: { value: 'test' } })

    // Should handle error without crashing - onSearch is still called
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith('test')
    }, { timeout: 500 })
  })

  it('does not search for queries shorter than 2 characters', async () => {
    render(
      <SearchBar
        onSearch={mockOnSearch}
        onResultClick={mockOnResultClick}
      />
    )

    const input = screen.getByPlaceholderText('Search...')
    fireEvent.change(input, { target: { value: 'a' } })

    // Wait a bit to make sure it doesn't call onSearch
    await new Promise(resolve => setTimeout(resolve, 400))

    expect(mockOnSearch).not.toHaveBeenCalled()
  })
})
