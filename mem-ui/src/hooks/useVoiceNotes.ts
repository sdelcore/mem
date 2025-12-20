import { useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE_URL } from '../utils/config'

export interface VoiceRecordingResponse {
  status: string
  transcription_id: number
  transcription: string
  speaker: string | null
  timestamp: string
  duration: number | null
  metadata: {
    duration: number | null
    language: string
  }
}

// Create voice recording mutation (creates a transcription, not an annotation)
export const useCreateVoiceNote = () => {
  const queryClient = useQueryClient()

  return useMutation<VoiceRecordingResponse, Error, Blob>({
    mutationFn: async (audioBlob) => {
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.webm')

      const response = await fetch(`${API_BASE_URL}/api/voice-notes`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create voice recording')
      }

      return response.json()
    },
    onSuccess: () => {
      // Invalidate timeline to show new transcription
      queryClient.invalidateQueries({ queryKey: ['timeline'] })
    },
  })
}
