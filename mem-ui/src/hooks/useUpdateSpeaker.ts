import { useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE_URL } from '../utils/config'

export interface UpdateSpeakerParams {
  transcription_id: number
  speaker_name: string
  speaker_id?: number | null
}

export interface UpdateSpeakerResponse {
  transcription_id: number
  speaker_name: string
  speaker_id: number | null
  speaker_confidence: number
  message: string
}

export const useUpdateSpeaker = () => {
  const queryClient = useQueryClient()

  return useMutation<UpdateSpeakerResponse, Error, UpdateSpeakerParams>({
    mutationFn: async ({ transcription_id, speaker_name, speaker_id }) => {
      const response = await fetch(
        `${API_BASE_URL}/api/transcriptions/${transcription_id}/speaker`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            speaker_name,
            speaker_id: speaker_id ?? null,
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update speaker')
      }

      return response.json()
    },
    onSuccess: () => {
      // Invalidate timeline to refresh with new speaker name
      queryClient.invalidateQueries({ queryKey: ['timeline'] })
    },
  })
}
