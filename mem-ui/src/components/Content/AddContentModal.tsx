import React, { useState, useRef } from 'react'
import { format } from 'date-fns'
import { X, Mic, Square, Send, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useCreateAnnotation } from '../../hooks/useAnnotations'
import { useTranscribe } from '../../hooks/useTranscribe'

interface AddContentModalProps {
  isOpen: boolean
  onClose: () => void
  timestamp: Date
  onContentCreated?: () => void
}

type RecordingState = 'idle' | 'recording' | 'transcribing'

const AddContentModal: React.FC<AddContentModalProps> = ({
  isOpen,
  onClose,
  timestamp,
  onContentCreated,
}) => {
  const [annotationText, setAnnotationText] = useState('')
  const [recordingState, setRecordingState] = useState<RecordingState>('idle')
  const [recordingDuration, setRecordingDuration] = useState(0)
  const [isSaving, setIsSaving] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const createAnnotation = useCreateAnnotation()
  const transcribe = useTranscribe()

  const resetState = () => {
    setAnnotationText('')
    setRecordingState('idle')
    setRecordingDuration(0)
    setIsSaving(false)
  }

  const handleClose = () => {
    if (recordingState === 'recording') {
      stopRecording()
    }
    resetState()
    onClose()
  }

  const handleSubmit = async () => {
    if (!annotationText.trim()) return

    setIsSaving(true)
    try {
      await createAnnotation.mutateAsync({
        timestamp,
        content: annotationText.trim(),
        annotation_type: 'user_note',
      })
      onContentCreated?.()
      handleClose()
    } catch (error) {
      console.error('Failed to create annotation:', error)
      toast.error('Failed to create annotation. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  const startRecording = async () => {
    if (!window.isSecureContext) {
      const currentUrl = window.location.href
      const httpsUrl = currentUrl.replace('http://', 'https://')
      toast.error(
        `Microphone access requires a secure connection (HTTPS). Please access the site via: ${httpsUrl}`,
        { duration: 6000 }
      )
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      let mimeType = 'audio/webm'
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = ''
      }

      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunksRef.current = []
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const mimeTypeActual = mediaRecorder.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: mimeTypeActual })

        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop())
          streamRef.current = null
        }

        setRecordingState('transcribing')
        try {
          const result = await transcribe.mutateAsync(blob)
          // Append transcription to existing text
          setAnnotationText(prev => {
            if (prev.trim()) {
              return prev.trim() + ' ' + result.text
            }
            return result.text
          })
        } catch (error) {
          console.error('Failed to transcribe recording:', error)
          toast.error('Failed to transcribe. Please try again or type your note.')
        } finally {
          setRecordingState('idle')
        }
      }

      mediaRecorder.start()
      setRecordingState('recording')
      setRecordingDuration(0)

      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1)
      }, 1000)

    } catch (error) {
      console.error('Failed to start recording:', error)
      toast.error('Failed to access microphone. Please ensure microphone permissions are granted.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && recordingState === 'recording') {
      mediaRecorderRef.current.stop()
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleMicClick = () => {
    if (recordingState === 'recording') {
      stopRecording()
    } else if (recordingState === 'idle') {
      startRecording()
    }
  }

  if (!isOpen) return null

  const isDisabled = recordingState === 'transcribing' || isSaving

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cream-200">
          <div>
            <h2 className="text-lg font-semibold text-forest-700">Add Note</h2>
            <p className="text-sm text-sage-500">
              {format(timestamp, 'MMM dd, yyyy HH:mm:ss')}
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-cream-100 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-sage-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <div className="space-y-4">
            {/* Textarea with mic button */}
            <div className="relative">
              <textarea
                value={annotationText}
                onChange={(e) => setAnnotationText(e.target.value)}
                placeholder={
                  recordingState === 'transcribing'
                    ? 'Transcribing...'
                    : 'Type your note or click the mic to record...'
                }
                className="w-full h-32 p-3 pr-12 border border-cream-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-300 resize-none disabled:bg-cream-50 disabled:text-sage-400"
                disabled={isDisabled}
                autoFocus
              />
              {/* Mic button inside textarea */}
              <button
                onClick={handleMicClick}
                disabled={recordingState === 'transcribing'}
                className={`absolute right-2 top-2 p-2 rounded-lg transition-all ${
                  recordingState === 'recording'
                    ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                    : recordingState === 'transcribing'
                    ? 'bg-sage-200 text-sage-400 cursor-not-allowed'
                    : 'bg-forest-100 hover:bg-forest-200 text-forest-600'
                }`}
                aria-label={recordingState === 'recording' ? 'Stop recording' : 'Start recording'}
              >
                {recordingState === 'recording' ? (
                  <Square className="w-5 h-5" />
                ) : recordingState === 'transcribing' ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Mic className="w-5 h-5" />
                )}
              </button>
            </div>

            {/* Recording indicator */}
            {recordingState === 'recording' && (
              <div className="flex items-center gap-2 text-sm text-red-600">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span>Recording: {formatDuration(recordingDuration)}</span>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleClose}
                className="flex-1 px-4 py-2.5 border border-cream-200 rounded-lg hover:bg-cream-50 transition-colors text-sage-600"
                disabled={isDisabled}
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!annotationText.trim() || isDisabled}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-forest-500 text-white rounded-lg hover:bg-forest-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Save Note
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AddContentModal
