import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE_URL } from '../utils/config'

export interface VoiceProfile {
  profile_id: number
  name: string
  display_name: string | null
  created_at: string
  updated_at: string
  metadata: Record<string, any> | null
}

export interface VoiceProfileListResponse {
  profiles: VoiceProfile[]
  count: number
}

// Fetch all voice profiles
export const useVoiceProfiles = () => {
  return useQuery<VoiceProfileListResponse>({
    queryKey: ['voice-profiles'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/voice-profiles`)
      if (!response.ok) {
        throw new Error('Failed to fetch voice profiles')
      }
      return response.json()
    },
    refetchInterval: 30000, // Poll every 30 seconds
  })
}

// Fetch single voice profile
export const useVoiceProfile = (profileId: number | null, enabled = true) => {
  return useQuery<VoiceProfile>({
    queryKey: ['voice-profile', profileId],
    queryFn: async () => {
      if (!profileId) throw new Error('No profile ID provided')
      const response = await fetch(`${API_BASE_URL}/api/voice-profiles/${profileId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch voice profile')
      }
      return response.json()
    },
    enabled: enabled && !!profileId,
  })
}

// Create voice profile mutation
export const useCreateVoiceProfile = () => {
  const queryClient = useQueryClient()

  return useMutation<VoiceProfile, Error, FormData>({
    mutationFn: async (formData) => {
      const response = await fetch(`${API_BASE_URL}/api/voice-profiles`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create voice profile')
      }

      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-profiles'] })
    },
  })
}

// Delete voice profile mutation
export const useDeleteVoiceProfile = () => {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, number>({
    mutationFn: async (profileId) => {
      const response = await fetch(`${API_BASE_URL}/api/voice-profiles/${profileId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete voice profile')
      }

      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-profiles'] })
    },
  })
}
