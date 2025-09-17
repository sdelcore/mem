import { useQuery } from '@tanstack/react-query'

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
  const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  
  const fetchTimelineData = async (): Promise<TimelineData[]> => {
    const params = new URLSearchParams({
      type: 'timeline', 
      start: startTime.toISOString(),
      end: endTime.toISOString(),
      limit: '5000',  // Increase limit to get all data for the time period
    })
    
    const response = await fetch(`${backendUrl}/api/search?${params}`)
    
    if (!response.ok) {
      throw new Error('Failed to fetch timeline data')
    }
    
    const data = await response.json()
    // Map backend response to frontend format
    return (data.entries || []).map((entry: any) => ({
      id: entry.frame?.frame_id || `${entry.timestamp}_${entry.source_id}`,
      timestamp: entry.timestamp,
      source_id: entry.source_id,
      source_type: entry.source_type,
      source_filename: entry.source_filename,
      source_location: entry.source_location,
      source_device_id: entry.source_device_id,
      frame: entry.frame ? {
        url: `${backendUrl}/api/search?type=frame&frame_id=${entry.frame.frame_id}`,
        hash: entry.frame.perceptual_hash,
        source_id: entry.frame.source_id
      } : undefined,
      transcript: entry.transcript?.text,
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
  const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  
  const searchContent = async () => {
    if (!query || query.trim().length < 2) {
      return { results: [] }
    }
    
    const response = await fetch(
      `${backendUrl}/api/search?type=transcript&q=${encodeURIComponent(query)}`
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