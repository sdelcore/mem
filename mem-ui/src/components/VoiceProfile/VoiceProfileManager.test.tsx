import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import VoiceProfileManager from './VoiceProfileManager'
import React from 'react'

// Mock the hooks
vi.mock('../../hooks/useVoiceProfiles', () => ({
  useVoiceProfiles: () => ({
    data: {
      profiles: [
        { profile_id: 1, name: 'alice', display_name: 'Alice', created_at: '2024-01-15T10:00:00' },
      ],
      count: 1,
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useCreateVoiceProfile: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  }),
  useDeleteVoiceProfile: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  }),
}))

describe('VoiceProfileManager', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )

  it('renders the voices button', () => {
    render(<VoiceProfileManager />, { wrapper })

    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('shows profile count badge when profiles exist', () => {
    render(<VoiceProfileManager />, { wrapper })

    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('opens dropdown when button is clicked', () => {
    render(<VoiceProfileManager />, { wrapper })

    const button = screen.getByRole('button')
    fireEvent.click(button)

    expect(screen.getByText('Voice Profiles')).toBeInTheDocument()
  })

  it('shows register button when dropdown is open', () => {
    render(<VoiceProfileManager />, { wrapper })

    const button = screen.getByRole('button')
    fireEvent.click(button)

    expect(screen.getByText('Register Voice Profile')).toBeInTheDocument()
  })
})
