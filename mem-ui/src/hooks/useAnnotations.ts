import { useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE_URL } from '../utils/config'

export interface QuickAnnotationResponse {
  status: string
  annotation_id: number
  source_id: number
  timestamp: string
  content: string
  annotation_type: string
}

export interface CreateAnnotationParams {
  timestamp: Date
  content: string
  annotation_type?: string
}

// Create quick annotation mutation
export const useCreateAnnotation = () => {
  const queryClient = useQueryClient()

  return useMutation<QuickAnnotationResponse, Error, CreateAnnotationParams>({
    mutationFn: async ({ timestamp, content, annotation_type = 'user_note' }) => {
      const params = new URLSearchParams({
        timestamp: timestamp.toISOString(),
        content,
        annotation_type,
      })

      const response = await fetch(`${API_BASE_URL}/api/annotations/quick?${params}`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create annotation')
      }

      return response.json()
    },
    onSuccess: () => {
      // Invalidate timeline to show new annotation
      queryClient.invalidateQueries({ queryKey: ['timeline'] })
    },
  })
}
