import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { API_BASE_URL } from '../utils/config'

// Backend settings types
export interface CaptureFrameSettings {
  interval_seconds: number
  jpeg_quality: number
  enable_deduplication: boolean
  similarity_threshold: number
}

export interface CaptureAudioSettings {
  chunk_duration_seconds: number
  sample_rate: number
}

export interface CaptureSettings {
  frame: CaptureFrameSettings
  audio: CaptureAudioSettings
}

export interface STTDSettings {
  model: string
  device: string
  compute_type: string
  enable_diarization: boolean
  speaker_identification: boolean
  min_speaker_confidence: number
}

export interface StreamingSettings {
  frame_interval_seconds: number
  max_concurrent_streams: number
}

export interface BackendSettings {
  capture: CaptureSettings
  sttd: STTDSettings
  streaming: StreamingSettings
}

export interface UpdateSettingsResponse {
  settings: BackendSettings
  restart_required: boolean
  restart_reason: string | null
}

// UI settings types (stored in localStorage)
export interface UISettings {
  timelineSegmentMinutes: number
  autoRefreshSeconds: number | null
  defaultViewMode: '6h' | '12h' | '24h'
}

const UI_SETTINGS_KEY = 'mem-ui-settings'

const DEFAULT_UI_SETTINGS: UISettings = {
  timelineSegmentMinutes: 5,
  autoRefreshSeconds: 30,
  defaultViewMode: '12h',
}

// Backend settings hook
export function useBackendSettings() {
  return useQuery<BackendSettings>({
    queryKey: ['settings'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/settings`)
      if (!response.ok) {
        throw new Error('Failed to fetch settings')
      }
      return response.json()
    },
    staleTime: 60000, // 1 minute
  })
}

export function useDefaultSettings() {
  return useQuery<BackendSettings>({
    queryKey: ['settings', 'defaults'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/settings/defaults`)
      if (!response.ok) {
        throw new Error('Failed to fetch default settings')
      }
      return response.json()
    },
    staleTime: Infinity, // Defaults never change
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()

  return useMutation<UpdateSettingsResponse, Error, Partial<BackendSettings>>({
    mutationFn: async (settings) => {
      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update settings')
      }
      return response.json()
    },
    onSuccess: (data) => {
      // Update the cached settings
      queryClient.setQueryData(['settings'], data.settings)
    },
  })
}

// UI settings hook (localStorage)
export function useUISettings() {
  const [settings, setSettingsState] = useState<UISettings>(() => {
    if (typeof window === 'undefined') return DEFAULT_UI_SETTINGS
    const stored = localStorage.getItem(UI_SETTINGS_KEY)
    if (stored) {
      try {
        return { ...DEFAULT_UI_SETTINGS, ...JSON.parse(stored) }
      } catch {
        return DEFAULT_UI_SETTINGS
      }
    }
    return DEFAULT_UI_SETTINGS
  })

  const setSettings = (newSettings: Partial<UISettings>) => {
    setSettingsState((prev) => {
      const updated = { ...prev, ...newSettings }
      localStorage.setItem(UI_SETTINGS_KEY, JSON.stringify(updated))
      return updated
    })
  }

  const resetToDefaults = () => {
    localStorage.removeItem(UI_SETTINGS_KEY)
    setSettingsState(DEFAULT_UI_SETTINGS)
  }

  return { settings, setSettings, resetToDefaults, defaults: DEFAULT_UI_SETTINGS }
}

// Combined settings hook for the settings page
export function useSettings() {
  const backendQuery = useBackendSettings()
  const defaultsQuery = useDefaultSettings()
  const updateMutation = useUpdateSettings()
  const uiSettings = useUISettings()

  return {
    backend: {
      data: backendQuery.data,
      defaults: defaultsQuery.data,
      isLoading: backendQuery.isLoading || defaultsQuery.isLoading,
      error: backendQuery.error || defaultsQuery.error,
      refetch: backendQuery.refetch,
    },
    ui: uiSettings,
    update: updateMutation,
  }
}
