import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useStreams, useCreateStream, useDeleteStream } from './useStreams'
import React from 'react'

// Mock fetch
global.fetch = vi.fn()

describe('useStreams', () => {
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

  it('fetches streams successfully', async () => {
    const mockData = {
      streams: [
        { session_id: '1', stream_key: 'key1', name: 'Stream 1', status: 'waiting' },
        { session_id: '2', stream_key: 'key2', name: 'Stream 2', status: 'live' },
      ],
      active_count: 1,
      total_count: 2,
    }

    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    })

    const { result } = renderHook(() => useStreams(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.streams).toHaveLength(2)
    expect(result.current.data?.active_count).toBe(1)
  })

  it('handles fetch error', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const testQueryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    const testWrapper = ({ children }: { children: React.ReactNode }) => (
      React.createElement(QueryClientProvider, { client: testQueryClient }, children)
    )

    const { result } = renderHook(() => useStreams(), { wrapper: testWrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeInstanceOf(Error)
  })
})

describe('useCreateStream', () => {
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

  it('creates stream successfully', async () => {
    const mockStream = {
      session_id: 'new-id',
      stream_key: 'new-key',
      name: 'New Stream',
      status: 'waiting',
    }

    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStream,
    })

    const { result } = renderHook(() => useCreateStream(), { wrapper })

    result.current.mutate({ name: 'New Stream' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.stream_key).toBe('new-key')
  })
})

describe('useDeleteStream', () => {
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

  it('deletes stream successfully', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'Stream deleted' }),
    })

    const { result } = renderHook(() => useDeleteStream(), { wrapper })

    result.current.mutate('stream-key')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.message).toBe('Stream deleted')
  })
})
