import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useVoiceProfiles, useCreateVoiceProfile, useDeleteVoiceProfile } from './useVoiceProfiles'
import React from 'react'

// Mock fetch
global.fetch = vi.fn()

describe('useVoiceProfiles', () => {
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

  it('fetches voice profiles successfully', async () => {
    const mockData = {
      profiles: [
        { profile_id: 1, name: 'alice', display_name: 'Alice', created_at: '2024-01-15T10:00:00' },
        { profile_id: 2, name: 'bob', display_name: 'Bob', created_at: '2024-01-15T11:00:00' },
      ],
      count: 2,
    }

    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    })

    const { result } = renderHook(() => useVoiceProfiles(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.profiles).toHaveLength(2)
    expect(result.current.data?.count).toBe(2)
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

    const { result } = renderHook(() => useVoiceProfiles(), { wrapper: testWrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeInstanceOf(Error)
  })
})

describe('useCreateVoiceProfile', () => {
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

  it('creates voice profile successfully', async () => {
    const mockProfile = {
      profile_id: 3,
      name: 'charlie',
      display_name: 'Charlie',
      created_at: '2024-01-15T12:00:00',
    }

    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockProfile,
    })

    const { result } = renderHook(() => useCreateVoiceProfile(), { wrapper })

    const formData = new FormData()
    formData.append('name', 'charlie')
    formData.append('display_name', 'Charlie')

    result.current.mutate(formData)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.profile_id).toBe(3)
  })

  it('handles creation error', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Profile already exists' }),
    })

    const { result } = renderHook(() => useCreateVoiceProfile(), { wrapper })

    const formData = new FormData()
    formData.append('name', 'existing')

    result.current.mutate(formData)

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error?.message).toBe('Profile already exists')
  })
})

describe('useDeleteVoiceProfile', () => {
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

  it('deletes voice profile successfully', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'Profile deleted' }),
    })

    const { result } = renderHook(() => useDeleteVoiceProfile(), { wrapper })

    result.current.mutate(1)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.message).toBe('Profile deleted')
  })
})
