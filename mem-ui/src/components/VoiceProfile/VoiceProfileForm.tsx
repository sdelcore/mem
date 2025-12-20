import React, { useState, useRef } from 'react'
import { Upload, Mic, X, Square, AudioLines } from 'lucide-react'
import { useCreateVoiceProfile } from '../../hooks/useVoiceProfiles'

interface VoiceProfileFormProps {
  onProfileCreated?: () => void
}

const VoiceProfileForm: React.FC<VoiceProfileFormProps> = ({ onProfileCreated }) => {
  const [showForm, setShowForm] = useState(false)
  const [displayName, setDisplayName] = useState('')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [inputMode, setInputMode] = useState<'upload' | 'record'>('upload')

  // Recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const createMutation = useCreateVoiceProfile()

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setAudioFile(file)
      setRecordedBlob(null)
    }
  }

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
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

      chunksRef.current = []
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setRecordedBlob(blob)
        stream.getTracks().forEach(track => track.stop())
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
      }
    }
  }

  const handleSubmit = async () => {
    const audioData = recordedBlob || audioFile
    if (!displayName || !audioData) return

    // Derive internal name from display name
    const internalName = displayName.toLowerCase().replace(/\s+/g, '_')

    const formData = new FormData()
    formData.append('name', internalName)
    formData.append('display_name', displayName)

    if (recordedBlob) {
      formData.append('file', recordedBlob, `${internalName}_recording.webm`)
    } else if (audioFile) {
      formData.append('file', audioFile)
    }

    try {
      await createMutation.mutateAsync(formData)
      resetForm()
      onProfileCreated?.()
    } catch (error) {
      console.error('Failed to create profile:', error)
    }
  }

  const resetForm = () => {
    setDisplayName('')
    setAudioFile(null)
    setRecordedBlob(null)
    setShowForm(false)
    setRecordingDuration(0)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const hasAudio = audioFile || recordedBlob

  return (
    <div className="border-b border-cream-200 p-4">
      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-center space-x-2 py-2 px-4 bg-sage-300 text-cream-50 rounded-lg hover:bg-sage-400 transition-colors"
        >
          <AudioLines className="w-4 h-4" />
          <span className="text-sm font-medium">Register Voice Profile</span>
        </button>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-forest-700">New Voice Profile</h3>
            <button onClick={resetForm} className="text-sage-400 hover:text-forest-600">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Name input */}
          <input
            type="text"
            placeholder="Full name (e.g., John Smith)"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-cream-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage-400"
          />

          {/* Input mode toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setInputMode('upload')}
              className={`flex-1 py-2 text-sm rounded-lg transition-colors flex items-center justify-center gap-1 ${
                inputMode === 'upload'
                  ? 'bg-sage-300 text-cream-50'
                  : 'bg-cream-100 text-forest-600 hover:bg-cream-200'
              }`}
            >
              <Upload className="w-4 h-4" />
              Upload
            </button>
            <button
              onClick={() => setInputMode('record')}
              className={`flex-1 py-2 text-sm rounded-lg transition-colors flex items-center justify-center gap-1 ${
                inputMode === 'record'
                  ? 'bg-sage-300 text-cream-50'
                  : 'bg-cream-100 text-forest-600 hover:bg-cream-200'
              }`}
            >
              <Mic className="w-4 h-4" />
              Record
            </button>
          </div>

          {/* Upload mode */}
          {inputMode === 'upload' && (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".wav,.mp3,.m4a,.webm,.ogg"
                onChange={handleFileSelect}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full py-3 border-2 border-dashed border-cream-300 rounded-lg text-sm text-sage-500 hover:border-sage-300 hover:text-sage-600 transition-colors"
              >
                {audioFile ? audioFile.name : 'Click to select audio file'}
              </button>
            </div>
          )}

          {/* Record mode */}
          {inputMode === 'record' && (
            <div className="flex items-center justify-center gap-4 py-4">
              {!isRecording && !recordedBlob && (
                <button
                  onClick={startRecording}
                  className="p-4 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                  title="Start recording"
                >
                  <Mic className="w-6 h-6" />
                </button>
              )}

              {isRecording && (
                <div className="flex items-center gap-4">
                  <button
                    onClick={stopRecording}
                    className="p-4 bg-red-500 text-white rounded-full animate-pulse"
                    title="Stop recording"
                  >
                    <Square className="w-6 h-6" />
                  </button>
                  <span className="text-sm text-forest-600">
                    Recording: {formatDuration(recordingDuration)}
                  </span>
                </div>
              )}

              {recordedBlob && !isRecording && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-sage-500">
                    Recorded: {formatDuration(recordingDuration)}
                  </span>
                  <button
                    onClick={() => {
                      setRecordedBlob(null)
                      setRecordingDuration(0)
                    }}
                    className="text-xs text-red-500 hover:underline"
                  >
                    Discard
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!displayName || !hasAudio || createMutation.isPending}
            className="w-full py-2 bg-sage-400 text-cream-50 rounded-lg hover:bg-sage-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createMutation.isPending ? 'Registering...' : 'Register Voice'}
          </button>

          {createMutation.isError && (
            <p className="text-xs text-red-600">{createMutation.error?.message}</p>
          )}
        </div>
      )}
    </div>
  )
}

export default VoiceProfileForm
