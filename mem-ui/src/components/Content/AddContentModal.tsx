import React, { useState, useRef } from 'react'
import { format } from 'date-fns'
import { X, MessageSquare, Mic, Square, Send } from 'lucide-react'
import { useCreateAnnotation } from '../../hooks/useAnnotations'
import { useCreateVoiceNote } from '../../hooks/useVoiceNotes'

interface AddContentModalProps {
  isOpen: boolean
  onClose: () => void
  timestamp: Date
  onContentCreated?: () => void
}

type ModalMode = 'select' | 'text' | 'voice'

const AddContentModal: React.FC<AddContentModalProps> = ({
  isOpen,
  onClose,
  timestamp,
  onContentCreated,
}) => {
  const [mode, setMode] = useState<ModalMode>('select')
  const [annotationText, setAnnotationText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const [isProcessing, setIsProcessing] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const createAnnotation = useCreateAnnotation()
  const createVoiceNote = useCreateVoiceNote()

  const resetState = () => {
    setMode('select')
    setAnnotationText('')
    setIsRecording(false)
    setRecordingDuration(0)
    setIsProcessing(false)
  }

  const handleClose = () => {
    if (isRecording) {
      stopRecording()
    }
    resetState()
    onClose()
  }

  const handleSubmitText = async () => {
    if (!annotationText.trim()) return

    setIsProcessing(true)
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
      alert('Failed to create annotation. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const startRecording = async () => {
    if (!window.isSecureContext) {
      const currentUrl = window.location.href
      const httpsUrl = currentUrl.replace('http://', 'https://')
      alert(
        `Microphone access requires a secure connection (HTTPS).\n\n` +
        `Please access the site via:\n${httpsUrl}`
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

        setIsProcessing(true)
        try {
          await createVoiceNote.mutateAsync(blob)
          onContentCreated?.()
          handleClose()
        } catch (error) {
          console.error('Failed to create voice recording:', error)
          alert('Failed to transcribe voice recording. Please try again.')
        } finally {
          setIsProcessing(false)
        }
      }

      mediaRecorder.start()
      setIsRecording(true)
      setRecordingDuration(0)

      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1)
      }, 1000)

    } catch (error) {
      console.error('Failed to start recording:', error)
      alert('Failed to access microphone. Please ensure microphone permissions are granted.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
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

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cream-200">
          <div>
            <h2 className="text-lg font-semibold text-forest-700">Add Content</h2>
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
          {mode === 'select' && (
            <div className="space-y-3">
              <p className="text-sm text-sage-600 mb-4">
                Choose what you'd like to add at this timestamp:
              </p>
              <button
                onClick={() => setMode('text')}
                className="w-full flex items-center gap-3 p-4 border border-cream-200 rounded-lg hover:bg-cream-50 transition-colors"
              >
                <div className="p-2 bg-sage-100 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-sage-600" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-forest-700">Add Text Note</p>
                  <p className="text-sm text-sage-500">Write a note or annotation</p>
                </div>
              </button>
              <button
                onClick={() => setMode('voice')}
                className="w-full flex items-center gap-3 p-4 border border-cream-200 rounded-lg hover:bg-cream-50 transition-colors"
              >
                <div className="p-2 bg-forest-100 rounded-lg">
                  <Mic className="w-5 h-5 text-forest-600" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-forest-700">Record Voice</p>
                  <p className="text-sm text-sage-500">Record and transcribe audio</p>
                </div>
              </button>
            </div>
          )}

          {mode === 'text' && (
            <div className="space-y-4">
              <div>
                <label htmlFor="annotation-text" className="block text-sm font-medium text-forest-700 mb-2">
                  Your note
                </label>
                <textarea
                  id="annotation-text"
                  value={annotationText}
                  onChange={(e) => setAnnotationText(e.target.value)}
                  placeholder="Type your note here..."
                  className="w-full h-32 p-3 border border-cream-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-300 resize-none"
                  autoFocus
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setMode('select')}
                  className="flex-1 px-4 py-2.5 border border-cream-200 rounded-lg hover:bg-cream-50 transition-colors text-sage-600"
                  disabled={isProcessing}
                >
                  Back
                </button>
                <button
                  onClick={handleSubmitText}
                  disabled={!annotationText.trim() || isProcessing}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-forest-500 text-white rounded-lg hover:bg-forest-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isProcessing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
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
          )}

          {mode === 'voice' && (
            <div className="space-y-4">
              <div className="text-center py-8">
                {isRecording ? (
                  <>
                    <div className="mb-4">
                      <div className="w-20 h-20 mx-auto bg-red-500 rounded-full flex items-center justify-center animate-pulse">
                        <Mic className="w-10 h-10 text-white" />
                      </div>
                    </div>
                    <p className="text-2xl font-mono text-forest-700 mb-2">
                      {formatDuration(recordingDuration)}
                    </p>
                    <p className="text-sm text-sage-500">Recording...</p>
                  </>
                ) : isProcessing ? (
                  <>
                    <div className="mb-4">
                      <div className="w-20 h-20 mx-auto bg-sage-300 rounded-full flex items-center justify-center">
                        <div className="w-10 h-10 border-4 border-white border-t-transparent rounded-full animate-spin" />
                      </div>
                    </div>
                    <p className="text-lg text-forest-700 mb-2">Transcribing...</p>
                    <p className="text-sm text-sage-500">Please wait while we process your recording</p>
                  </>
                ) : (
                  <>
                    <div className="mb-4">
                      <div className="w-20 h-20 mx-auto bg-forest-100 rounded-full flex items-center justify-center">
                        <Mic className="w-10 h-10 text-forest-600" />
                      </div>
                    </div>
                    <p className="text-lg text-forest-700 mb-2">Ready to record</p>
                    <p className="text-sm text-sage-500">Click the button below to start recording</p>
                  </>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setMode('select')}
                  className="flex-1 px-4 py-2.5 border border-cream-200 rounded-lg hover:bg-cream-50 transition-colors text-sage-600"
                  disabled={isRecording || isProcessing}
                >
                  Back
                </button>
                {isRecording ? (
                  <button
                    onClick={stopRecording}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  >
                    <Square className="w-4 h-4" />
                    Stop Recording
                  </button>
                ) : (
                  <button
                    onClick={startRecording}
                    disabled={isProcessing}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-forest-500 text-white rounded-lg hover:bg-forest-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Mic className="w-4 h-4" />
                    Start Recording
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AddContentModal
