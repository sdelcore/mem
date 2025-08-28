import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useTimeline, useSearch } from './useTimeline'
import React from 'react'

// Mock fetch
global.fetch = vi.fn()

describe('useTimeline', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    React.createElement(QueryClientProvider, { client: queryClient }, children)
  )

  it('fetches timeline data successfully', async () => {
    const mockData = {
      items: [
        { id: '1', timestamp: '2024-01-15T10:00:00' },
        { id: '2', timestamp: '2024-01-15T10:01:00' },
      ],
    }

    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    })

    const startTime = new Date('2024-01-15T10:00:00')
    const endTime = new Date('2024-01-15T11:00:00')

    const { result } = renderHook(
      () => useTimeline(startTime, endTime),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockData.items)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/timeline?')
    )
  })

  it('handles fetch error', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const startTime = new Date('2024-01-15T10:00:00')
    const endTime = new Date('2024-01-15T11:00:00')

    const { result } = renderHook(
      () => useTimeline(startTime, endTime),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeInstanceOf(Error)
    expect(result.current.error?.message).toBe('Failed to fetch timeline data')
  })

  it('uses custom refetch interval', () => {
    const startTime = new Date('2024-01-15T10:00:00')
    const endTime = new Date('2024-01-15T11:00:00')

    const { result } = renderHook(
      () => useTimeline(startTime, endTime, { refetchInterval: 5000 }),
      { wrapper }
    )

    expect(result.current).toBeDefined()
  })

  it('can be disabled', () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    
    const startTime = new Date('2024-01-15T10:00:00')
    const endTime = new Date('2024-01-15T11:00:00')

    renderHook(
      () => useTimeline(startTime, endTime, { enabled: false }),
      { wrapper }
    )

    expect(mockFetch).not.toHaveBeenCalled()
  })
})

describe('useSearch', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    React.createElement(QueryClientProvider, { client: queryClient }, children)
  )

  it('searches content successfully', async () => {
    const mockResults = {
      results: [
        { id: '1', text: 'Test result 1' },
        { id: '2', text: 'Test result 2' },
      ],
    }

    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResults,
    })

    const { result } = renderHook(
      () => useSearch('test query'),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockResults)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/search?q=test%20query')
    )
  })

  it('does not search for short queries', () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>

    renderHook(() => useSearch('a'), { wrapper })

    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('returns empty results for empty query', async () => {
    const { result } = renderHook(
      () => useSearch(''),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual({ results: [] })
  })

  it('handles search error', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const { result } = renderHook(
      () => useSearch('test query'),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeInstanceOf(Error)
    expect(result.current.error?.message).toBe('Search failed')
  })

  it('can be disabled', () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>

    renderHook(
      () => useSearch('test query', false),
      { wrapper }
    )

    expect(mockFetch).not.toHaveBeenCalled()
  })
})