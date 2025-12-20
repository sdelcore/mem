import { useQuery } from '@tanstack/react-query'
import { API_BASE_URL } from '../utils/config'

interface TimelineData {
  id: string
  timestamp: string
  source_id: number
  source_type?: string
  source_filename?: string
  source_location?: string
  source_device_id?: string
  frame?: {
    url: string
    hash?: string
    source_id: number
  }
  transcript?: string
  speaker_name?: string
  speaker_confidence?: number
  annotations?: string[]
}

interface UseTimelineOptions {
  refetchInterval?: number
  enabled?: boolean
}

export const useTimeline = (
  startTime: Date,
  endTime: Date,
  options?: UseTimelineOptions
) => {
  const fetchTimelineData = async (): Promise<TimelineData[]> => {
    const params = new URLSearchParams({
      type: 'timeline',
      start: startTime.toISOString(),
      end: endTime.toISOString(),
      limit: '5000',
    })

    const response = await fetch(`${API_BASE_URL}/api/search?${params}`)

    if (!response.ok) {
      throw new Error('Failed to fetch timeline data')
    }

    const data = await response.json()
    return (data.entries || []).map((entry: any) => ({
      id: entry.frame?.frame_id || `${entry.timestamp}_${entry.source_id}`,
      timestamp: entry.timestamp,
      source_id: entry.source_id,
      source_type: entry.source_type,
      source_filename: entry.source_filename,
      source_location: entry.source_location,
      source_device_id: entry.source_device_id,
      frame: entry.frame ? {
        url: `${API_BASE_URL}/api/search?type=frame&frame_id=${entry.frame.frame_id}`,
        hash: entry.frame.perceptual_hash,
        source_id: entry.frame.source_id
      } : undefined,
      transcript: entry.transcript?.text,
      speaker_name: entry.transcript?.speaker_name,
      speaker_confidence: entry.transcript?.speaker_confidence,
      annotations: entry.annotations || []
    }))
  }
  
  return useQuery({
    queryKey: ['timeline', startTime.toISOString(), endTime.toISOString()],
    queryFn: fetchTimelineData,
    refetchInterval: options?.refetchInterval || 30000, // Re-enable 30 second refresh
    enabled: options?.enabled !== false,
    retry: 2,
    retryDelay: 1000,
  })
}

export const useSearch = (query: string, enabled = true) => {
  const searchContent = async () => {
    if (!query || query.trim().length < 2) {
      return { results: [] }
    }

    const response = await fetch(
      `${API_BASE_URL}/api/search?type=transcript&q=${encodeURIComponent(query)}`
    )
    
    if (!response.ok) {
      throw new Error('Search failed')
    }
    
    return response.json()
  }
  
  return useQuery({
    queryKey: ['search', query],
    queryFn: searchContent,
    enabled: enabled && query.trim().length >= 2,
    staleTime: 60000, // Cache for 1 minute
  })
}