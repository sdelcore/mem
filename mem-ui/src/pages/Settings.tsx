import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Save, RotateCcw, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useSettings } from '../hooks/useSettings'
import {
  SettingSection,
  SettingSlider,
  SettingToggle,
  SettingDropdown,
} from '../components/Settings'

function Settings() {
  const { backend, ui, update } = useSettings()

  // Local state for form values
  const [captureFrame, setCaptureFrame] = useState({
    interval_seconds: 5,
    jpeg_quality: 85,
    enable_deduplication: true,
    similarity_threshold: 95,
  })

  const [captureAudio, setCaptureAudio] = useState({
    chunk_duration_seconds: 300,
    sample_rate: 16000,
  })

  const [sttd, setSttd] = useState({
    model: 'large-v3',
    device: 'cuda',
    compute_type: 'float16',
    enable_diarization: true,
    speaker_identification: true,
    min_speaker_confidence: 0.7,
  })

  const [streaming, setStreaming] = useState({
    frame_interval_seconds: 1,
    max_concurrent_streams: 10,
  })

  const [uiSettings, setUiSettings] = useState(ui.settings)
  const [hasChanges, setHasChanges] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [restartWarning, setRestartWarning] = useState<string | null>(null)

  // Sync form state with fetched data
  useEffect(() => {
    if (backend.data) {
      setCaptureFrame(backend.data.capture.frame)
      setCaptureAudio(backend.data.capture.audio)
      setSttd(backend.data.sttd)
      setStreaming(backend.data.streaming)
    }
  }, [backend.data])

  useEffect(() => {
    setUiSettings(ui.settings)
  }, [ui.settings])

  // Track changes
  useEffect(() => {
    if (!backend.data) return

    const backendChanged =
      JSON.stringify(captureFrame) !== JSON.stringify(backend.data.capture.frame) ||
      JSON.stringify(captureAudio) !== JSON.stringify(backend.data.capture.audio) ||
      JSON.stringify(sttd) !== JSON.stringify(backend.data.sttd) ||
      JSON.stringify(streaming) !== JSON.stringify(backend.data.streaming)

    const uiChanged = JSON.stringify(uiSettings) !== JSON.stringify(ui.settings)

    setHasChanges(backendChanged || uiChanged)
  }, [captureFrame, captureAudio, sttd, streaming, uiSettings, backend.data, ui.settings])

  const handleSave = async () => {
    // Save UI settings to localStorage
    ui.setSettings(uiSettings)

    // Save backend settings
    try {
      const result = await update.mutateAsync({
        capture: {
          frame: captureFrame,
          audio: captureAudio,
        },
        sttd,
        streaming,
      })

      if (result.restart_required) {
        setRestartWarning(result.restart_reason || 'Some changes require a restart to take effect.')
        toast.success('Settings saved! Restart required for some changes.')
      } else {
        setRestartWarning(null)
        toast.success('Settings saved successfully!')
      }

      setSaveSuccess(true)
      setHasChanges(false)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (error) {
      console.error('Failed to save settings:', error)
      toast.error('Failed to save settings. Please try again.')
    }
  }

  const handleReset = () => {
    if (backend.defaults) {
      setCaptureFrame(backend.defaults.capture.frame)
      setCaptureAudio(backend.defaults.capture.audio)
      setSttd(backend.defaults.sttd)
      setStreaming(backend.defaults.streaming)
    }
    setUiSettings(ui.defaults)
  }

  const handleCancel = () => {
    if (backend.data) {
      setCaptureFrame(backend.data.capture.frame)
      setCaptureAudio(backend.data.capture.audio)
      setSttd(backend.data.sttd)
      setStreaming(backend.data.streaming)
    }
    setUiSettings(ui.settings)
    setHasChanges(false)
  }

  if (backend.isLoading) {
    return (
      <div className="min-h-screen bg-cream-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-forest-500 animate-spin" />
          <p className="text-sage-500">Loading settings...</p>
        </div>
      </div>
    )
  }

  if (backend.error) {
    return (
      <div className="min-h-screen bg-cream-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-red-500" />
          <h2 className="text-lg font-semibold text-forest-700">Failed to load settings</h2>
          <p className="text-sage-500">{backend.error.message}</p>
          <button
            onClick={() => backend.refetch()}
            className="px-4 py-2 bg-forest-500 text-cream-50 rounded-lg hover:bg-forest-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream-50">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-cream-100/90 backdrop-blur-lg border-b border-sage-200/50 shadow-sm">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 sm:h-16">
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="p-2 -ml-2 rounded-lg hover:bg-forest-100 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-forest-600" />
              </Link>
              <div>
                <h1 className="text-lg sm:text-xl font-bold text-forest-600">Settings</h1>
                <p className="hidden sm:block text-xs text-sage-400">Configure capture and transcription</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {saveSuccess && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Saved</span>
                </div>
              )}
              {hasChanges && (
                <span className="text-sm text-sage-500">Unsaved changes</span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Restart Warning */}
        {restartWarning && (
          <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-amber-800">Restart Required</h4>
              <p className="text-sm text-amber-700 mt-1">{restartWarning}</p>
            </div>
          </div>
        )}

        {/* Capture Settings */}
        <SettingSection
          title="Capture Settings"
          description="Configure frame extraction and image quality"
        >
          <SettingSlider
            label="Frame Interval"
            value={captureFrame.interval_seconds}
            min={1}
            max={60}
            unit="s"
            description="How often to capture frames from video/stream"
            onChange={(value) =>
              setCaptureFrame((prev) => ({ ...prev, interval_seconds: value }))
            }
          />

          <SettingSlider
            label="JPEG Quality"
            value={captureFrame.jpeg_quality}
            min={50}
            max={100}
            unit="%"
            description="Higher quality = larger files, better image detail"
            onChange={(value) =>
              setCaptureFrame((prev) => ({ ...prev, jpeg_quality: value }))
            }
          />

          <SettingToggle
            label="Frame Deduplication"
            value={captureFrame.enable_deduplication}
            description="Skip storing visually identical frames to save storage"
            onChange={(value) =>
              setCaptureFrame((prev) => ({ ...prev, enable_deduplication: value }))
            }
          />

          {captureFrame.enable_deduplication && (
            <SettingSlider
              label="Similarity Threshold"
              value={captureFrame.similarity_threshold}
              min={80}
              max={100}
              step={0.5}
              unit="%"
              description="Frames more similar than this are considered duplicates"
              onChange={(value) =>
                setCaptureFrame((prev) => ({ ...prev, similarity_threshold: value }))
              }
            />
          )}

          <SettingDropdown
            label="Audio Chunk Duration"
            value={String(captureAudio.chunk_duration_seconds)}
            options={[
              { value: '60', label: '1 minute' },
              { value: '150', label: '2.5 minutes' },
              { value: '300', label: '5 minutes' },
              { value: '600', label: '10 minutes' },
            ]}
            description="Duration of audio chunks for transcription processing"
            onChange={(value) =>
              setCaptureAudio((prev) => ({ ...prev, chunk_duration_seconds: Number(value) }))
            }
          />
        </SettingSection>

        {/* Transcription Settings */}
        <SettingSection
          title="Transcription Settings"
          description="Configure Whisper model and speaker identification"
          requiresRestart
        >
          <SettingDropdown
            label="Whisper Model"
            value={sttd.model}
            options={[
              { value: 'tiny', label: 'Tiny (fastest, least accurate)' },
              { value: 'base', label: 'Base (fast, good for clear speech)' },
              { value: 'small', label: 'Small (balanced)' },
              { value: 'medium', label: 'Medium (accurate, slower)' },
              { value: 'large-v3', label: 'Large V3 (most accurate, slowest)' },
            ]}
            description="Larger models are more accurate but require more memory and processing time"
            onChange={(value) => setSttd((prev) => ({ ...prev, model: value }))}
          />

          <SettingDropdown
            label="Device"
            value={sttd.device}
            options={[
              { value: 'cuda', label: 'CUDA (GPU - recommended)' },
              { value: 'cpu', label: 'CPU (slower, no GPU required)' },
            ]}
            description="Use CUDA for GPU acceleration if available"
            onChange={(value) => setSttd((prev) => ({ ...prev, device: value }))}
          />

          <SettingDropdown
            label="Compute Type"
            value={sttd.compute_type}
            options={[
              { value: 'float16', label: 'Float16 (GPU, faster)' },
              { value: 'int8', label: 'Int8 (CPU, lower memory)' },
              { value: 'float32', label: 'Float32 (highest precision)' },
            ]}
            description="Float16 recommended for GPU, Int8 for CPU"
            onChange={(value) => setSttd((prev) => ({ ...prev, compute_type: value }))}
          />

          <SettingToggle
            label="Speaker Identification"
            value={sttd.speaker_identification}
            description="Identify speakers using registered voice profiles"
            onChange={(value) =>
              setSttd((prev) => ({ ...prev, speaker_identification: value }))
            }
          />

          {sttd.speaker_identification && (
            <SettingSlider
              label="Min Speaker Confidence"
              value={sttd.min_speaker_confidence}
              min={0.5}
              max={0.95}
              step={0.05}
              description="Minimum confidence required to identify a speaker"
              onChange={(value) =>
                setSttd((prev) => ({ ...prev, min_speaker_confidence: value }))
              }
            />
          )}
        </SettingSection>

        {/* Streaming Settings */}
        <SettingSection
          title="Streaming Settings"
          description="Configure live stream capture"
        >
          <SettingSlider
            label="Stream Frame Interval"
            value={streaming.frame_interval_seconds}
            min={1}
            max={10}
            unit="s"
            description="How often to capture frames from live streams"
            onChange={(value) =>
              setStreaming((prev) => ({ ...prev, frame_interval_seconds: value }))
            }
          />

          <SettingSlider
            label="Max Concurrent Streams"
            value={streaming.max_concurrent_streams}
            min={1}
            max={20}
            description="Maximum number of simultaneous RTMP streams"
            onChange={(value) =>
              setStreaming((prev) => ({ ...prev, max_concurrent_streams: value }))
            }
          />
        </SettingSection>

        {/* UI Settings */}
        <SettingSection
          title="UI Settings"
          description="Configure timeline display preferences (stored in browser)"
        >
          <SettingDropdown
            label="Timeline Segment Duration"
            value={String(uiSettings.timelineSegmentMinutes)}
            options={[
              { value: '1', label: '1 minute' },
              { value: '5', label: '5 minutes' },
              { value: '10', label: '10 minutes' },
              { value: '15', label: '15 minutes' },
              { value: '30', label: '30 minutes' },
            ]}
            description="Duration of each segment in the timeline view"
            onChange={(value) =>
              setUiSettings((prev) => ({ ...prev, timelineSegmentMinutes: Number(value) }))
            }
          />

          <SettingDropdown
            label="Auto-Refresh Interval"
            value={String(uiSettings.autoRefreshSeconds ?? 'off')}
            options={[
              { value: 'off', label: 'Off' },
              { value: '10', label: '10 seconds' },
              { value: '30', label: '30 seconds' },
              { value: '60', label: '1 minute' },
            ]}
            description="How often to refresh timeline data"
            onChange={(value) =>
              setUiSettings((prev) => ({
                ...prev,
                autoRefreshSeconds: value === 'off' ? null : Number(value),
              }))
            }
          />

          <SettingDropdown
            label="Default View Mode"
            value={uiSettings.defaultViewMode}
            options={[
              { value: '6h', label: '6 hours' },
              { value: '12h', label: '12 hours' },
              { value: '24h', label: '24 hours' },
            ]}
            description="Default time range when opening the timeline"
            onChange={(value) =>
              setUiSettings((prev) => ({
                ...prev,
                defaultViewMode: value as '6h' | '12h' | '24h',
              }))
            }
          />
        </SettingSection>
      </main>

      {/* Sticky Footer */}
      <footer className="sticky bottom-0 bg-cream-100/90 backdrop-blur-lg border-t border-sage-200/50 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2.5 text-sage-600 hover:bg-cream-200 rounded-lg transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Reset to Defaults</span>
            </button>

            <div className="flex items-center gap-3">
              <button
                onClick={handleCancel}
                disabled={!hasChanges}
                className="px-4 py-2.5 text-sage-600 hover:bg-cream-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges || update.isPending}
                className="flex items-center gap-2 px-6 py-2.5 bg-forest-500 text-cream-50 rounded-lg hover:bg-forest-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {update.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Settings
