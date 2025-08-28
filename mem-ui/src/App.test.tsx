import { describe, it, expect, vi } from 'vitest'
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

describe('App', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  it('renders the main header', () => {
    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )
    
    expect(screen.getByText('Mem Timeline Viewer')).toBeInTheDocument()
  })

  it('renders timeline section', () => {
    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )
    
    expect(screen.getByText('Timeline')).toBeInTheDocument()
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

  it('shows loading state when timeline is loading', () => {
    vi.mock('./hooks/useTimeline', () => ({
      useTimeline: () => ({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      }),
    }))

    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )
  })

  it('shows error state when timeline fails to load', () => {
    vi.mock('./hooks/useTimeline', () => ({
      useTimeline: () => ({
        data: null,
        isLoading: false,
        error: new Error('Failed to load'),
        refetch: vi.fn(),
      }),
    }))

    render(
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(App)
      )
    )
  })
})