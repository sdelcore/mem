import { useMutation } from '@tanstack/react-query'
import { API_BASE_URL } from '../utils/config'

export interface TranscribeResponse {
  status: string
  text: string
  language: string
  duration: number
}

// Transcribe audio without saving to database
export const useTranscribe = () => {
  return useMutation<TranscribeResponse, Error, Blob>({
    mutationFn: async (audioBlob) => {
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.webm')

      const response = await fetch(`${API_BASE_URL}/api/transcribe`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to transcribe audio')
      }

      return response.json()
    },
    // Note: No onSuccess invalidation since we don't save anything
  })
}
