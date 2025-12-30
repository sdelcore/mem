import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE_URL } from '../utils/config'

export interface StreamSession {
  session_id: string
  stream_key: string
  name: string | null
  status: 'waiting' | 'live' | 'ended' | 'error'
  source_id: number | null
  rtmp_url: string
  started_at: string | null
  ended_at: string | null
  resolution: string | null
  frames_received: number
  frames_stored: number
  duration: number | null
}

export interface StreamListResponse {
  streams: StreamSession[]
  active_count: number
  total_count: number
}

export interface CreateStreamRequest {
  name?: string
  metadata?: Record<string, any>
}

// Fetch all streams
export const useStreams = (pollInterval?: number) => {
  return useQuery<StreamListResponse>({
    queryKey: ['streams'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/streams`)
      if (!response.ok) {
        throw new Error('Failed to fetch streams')
      }
      return response.json()
    },
    refetchInterval: pollInterval || 5000, // Poll every 5 seconds by default
  })
}

// Fetch single stream
export const useStream = (streamKey: string | null, enabled = true) => {
  return useQuery<StreamSession>({
    queryKey: ['stream', streamKey],
    queryFn: async () => {
      if (!streamKey) throw new Error('No stream key provided')
      const response = await fetch(`${API_BASE_URL}/api/streams/${streamKey}`)
      if (!response.ok) {
        throw new Error('Failed to fetch stream')
      }
      return response.json()
    },
    enabled: enabled && !!streamKey,
    refetchInterval: 2000, // Poll more frequently for individual stream
  })
}

// Create stream mutation
export const useCreateStream = () => {
  const queryClient = useQueryClient()
  
  return useMutation<StreamSession, Error, CreateStreamRequest>({
    mutationFn: async (data) => {
      const response = await fetch(`${API_BASE_URL}/api/streams/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create stream')
      }
      
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['streams'] })
    },
  })
}

// Stop stream mutation
export const useStopStream = () => {
  const queryClient = useQueryClient()
  
  return useMutation<{ message: string }, Error, string>({
    mutationFn: async (streamKey) => {
      const response = await fetch(`${API_BASE_URL}/api/streams/${streamKey}/stop`, {
        method: 'POST',
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to stop stream')
      }
      
      return response.json()
    },
    onSuccess: (_, streamKey) => {
      queryClient.invalidateQueries({ queryKey: ['streams'] })
      queryClient.invalidateQueries({ queryKey: ['stream', streamKey] })
    },
  })
}

// Delete stream mutation
export const useDeleteStream = () => {
  const queryClient = useQueryClient()
  
  return useMutation<{ message: string }, Error, string>({
    mutationFn: async (streamKey) => {
      const response = await fetch(`${API_BASE_URL}/api/streams/${streamKey}`, {
        method: 'DELETE',
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete stream')
      }
      
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['streams'] })
    },
  })
}

// Helper function to copy text to clipboard
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
    return false
  }
}