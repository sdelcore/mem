import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import React from 'react'

// Mock the hooks
vi.mock('./hooks/useTimeline', () => ({
  useTimeline: () => ({
    data: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

// Mock the useStreams hook
vi.mock('./hooks/useStreams', () => ({
  useStreams: () => ({
    data: { streams: [] },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

// Mock the useVoiceProfiles hook
vi.mock('./hooks/useVoiceProfiles', () => ({
  useVoiceProfiles: () => ({
    data: { profiles: [], count: 0 },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

describe('App', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
  })

  it('renders the main header', () => {
    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )

    expect(screen.getByText('Mem Timeline')).toBeInTheDocument()
  })

  it('renders date display with today view', () => {
    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )

    // Should have a Today button
    expect(screen.getByText('Today')).toBeInTheDocument()
  })

  it('renders search bar', () => {
    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )

    expect(screen.getByPlaceholderText('Search transcripts...')).toBeInTheDocument()
  })

  it('renders view mode buttons', () => {
    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )

    // View mode toggle buttons
    expect(screen.getByText('6h')).toBeInTheDocument()
    expect(screen.getByText('12h')).toBeInTheDocument()
    expect(screen.getByText('24h')).toBeInTheDocument()
  })

  it('renders upload button', () => {
    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )

    expect(screen.getByText(/Upload/i)).toBeInTheDocument()
  })
})
