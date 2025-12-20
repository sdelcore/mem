import React, { useState, useRef } from 'react'
import { Mic, Square } from 'lucide-react'
import { useCreateVoiceNote } from '../../hooks/useVoiceNotes'

const VoiceRecorder: React.FC = () => {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const createVoiceNote = useCreateVoiceNote()

  const startRecording = async () => {
    // Check for secure context - getUserMedia requires HTTPS on non-localhost
    if (!window.isSecureContext) {
      const currentUrl = window.location.href
      const httpsUrl = currentUrl.replace('http://', 'https://')
      alert(
        `Microphone access requires a secure connection (HTTPS).\n\n` +
        `Please access the site via:\n${httpsUrl}\n\n` +
        `You may need to accept the self-signed certificate warning.`
      )
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Try to use webm, fall back to default
      let mimeType = 'audio/webm'
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = ''  // Use browser default
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

        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop())
          streamRef.current = null
        }

        // Upload and transcribe
        setIsTranscribing(true)
        try {
          const result = await createVoiceNote.mutateAsync(blob)
          console.log('Voice note created:', result)
        } catch (error) {
          console.error('Failed to create voice note:', error)
          alert('Failed to transcribe voice note. Please try again.')
        } finally {
          setIsTranscribing(false)
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

  const handleClick = () => {
    if (isRecording) {
      stopRecording()
    } else if (!isTranscribing) {
      startRecording()
    }
  }

  // Recording state - red pulsing button with timer
  if (isRecording) {
    return (
      <button
        onClick={handleClick}
        className="flex items-center space-x-2 px-4 py-2.5 min-h-11 rounded-lg bg-red-500 text-white animate-pulse"
        title="Stop recording"
      >
        <Square className="w-5 h-5" />
        <span className="font-medium">{formatDuration(recordingDuration)}</span>
      </button>
    )
  }

  // Transcribing state - disabled with spinner
  if (isTranscribing) {
    return (
      <button
        disabled
        className="flex items-center space-x-2 px-4 py-2.5 min-h-11 rounded-lg bg-sage-300 text-cream-50 opacity-75"
      >
        <div className="w-5 h-5 border-2 border-cream-50 border-t-transparent rounded-full animate-spin" />
        <span className="font-medium hidden sm:inline">Transcribing...</span>
      </button>
    )
  }

  // Idle state - normal record button
  return (
    <button
      onClick={handleClick}
      className="flex items-center space-x-2 px-4 py-2.5 min-h-11 rounded-lg transition-all bg-sage-400 text-cream-50 hover:bg-sage-500"
      title="Record voice note"
    >
      <Mic className="w-5 h-5" />
      <span className="font-medium hidden sm:inline">Record</span>
    </button>
  )
}

export default VoiceRecorder
