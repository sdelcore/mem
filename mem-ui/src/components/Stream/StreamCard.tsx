import React, { useState } from 'react'
import { Camera, Play, Square, Copy, Trash2, Circle, AlertCircle } from 'lucide-react'
import { StreamSession, useStartStream, useStopStream, useDeleteStream, copyToClipboard } from '../../hooks/useStreams'
import { format } from 'date-fns'

interface StreamCardProps {
  stream: StreamSession
  onRefresh?: () => void
}

const StreamCard: React.FC<StreamCardProps> = ({ stream, onRefresh }) => {
  const [showDetails, setShowDetails] = useState(false)
  const [copied, setCopied] = useState<'url' | 'key' | null>(null)
  
  const startMutation = useStartStream()
  const stopMutation = useStopStream()
  const deleteMutation = useDeleteStream()

  const isLoading = startMutation.isPending || stopMutation.isPending || deleteMutation.isPending

  const handleCopy = async (text: string, type: 'url' | 'key') => {
    const success = await copyToClipboard(text)
    if (success) {
      setCopied(type)
      setTimeout(() => setCopied(null), 2000)
    }
  }

  const handleStart = async () => {
    try {
      await startMutation.mutateAsync(stream.stream_key)
      onRefresh?.()
    } catch (error) {
      console.error('Failed to start stream:', error)
    }
  }

  const handleStop = async () => {
    try {
      await stopMutation.mutateAsync(stream.stream_key)
      onRefresh?.()
    } catch (error) {
      console.error('Failed to stop stream:', error)
    }
  }

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this stream?')) {
      try {
        await deleteMutation.mutateAsync(stream.stream_key)
        onRefresh?.()
      } catch (error) {
        console.error('Failed to delete stream:', error)
      }
    }
  }

  const getStatusIcon = () => {
    switch (stream.status) {
      case 'live':
        return (
          <div className="flex items-center space-x-1">
            <Circle className="w-3 h-3 fill-red-500 text-red-500 animate-pulse" />
            <span className="text-sm font-medium text-red-600">Live</span>
          </div>
        )
      case 'waiting':
        return (
          <div className="flex items-center space-x-1">
            <Circle className="w-3 h-3 fill-amber-500 text-amber-500" />
            <span className="text-sm font-medium text-amber-600">Waiting</span>
          </div>
        )
      case 'ended':
        return (
          <div className="flex items-center space-x-1">
            <Circle className="w-3 h-3 fill-sage-200 text-sage-200" />
            <span className="text-sm font-medium text-sage-400">Ended</span>
          </div>
        )
      case 'error':
        return (
          <div className="flex items-center space-x-1">
            <AlertCircle className="w-3 h-3 text-red-500" />
            <span className="text-sm font-medium text-red-600">Error</span>
          </div>
        )
    }
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    }
    return `${secs}s`
  }

  return (
    <div className="border border-cream-200 rounded-lg p-4 hover:shadow-flat transition-shadow">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <Camera className="w-5 h-5 text-forest-500" />
          <div>
            <p className="text-sm font-medium text-forest-700">
              {stream.name || 'Unnamed Stream'}
            </p>
            <p className="text-xs text-sage-500">
              {stream.stream_key.substring(0, 8)}...
              {stream.resolution && ` • ${stream.resolution}`}
            </p>
          </div>
        </div>
        {getStatusIcon()}
      </div>

      {/* Stats */}
      {stream.status === 'live' && (
        <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
          <div className="text-center">
            <p className="text-sage-400">Duration</p>
            <p className="font-medium text-forest-700">
              {stream.duration ? formatDuration(stream.duration) : '0s'}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sage-400">Frames</p>
            <p className="font-medium text-forest-700">
              {stream.frames_stored}/{stream.frames_received}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sage-400">Started</p>
            <p className="font-medium text-forest-700">
              {stream.started_at ? format(new Date(stream.started_at), 'HH:mm') : '-'}
            </p>
          </div>
        </div>
      )}

      {/* RTMP Details */}
      <div className={`space-y-2 mb-3 ${showDetails ? '' : 'hidden'}`}>
        <div className="bg-cream-50 rounded p-2 border border-cream-200">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-sage-600">RTMP Server URL</p>
            <button
              onClick={() => handleCopy('rtmp://localhost:1935/live', 'url')}
              className="flex items-center space-x-1 px-2 py-1 text-xs bg-white rounded hover:bg-forest-50 transition-colors"
              title="Copy RTMP URL"
            >
              <Copy className="w-3 h-3 text-forest-600" />
              {copied === 'url' ? (
                <span className="text-sage-500 font-medium">Copied!</span>
              ) : (
                <span className="text-forest-600">Copy</span>
              )}
            </button>
          </div>
          <p className="text-xs font-mono text-forest-700 bg-white rounded px-2 py-1">
            rtmp://localhost:1935/live
          </p>
        </div>
        
        <div className="bg-cream-50 rounded p-2 border border-cream-200">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-sage-600">Stream Key (Required)</p>
            <button
              onClick={() => handleCopy(stream.stream_key, 'key')}
              className="flex items-center space-x-1 px-2 py-1 text-xs bg-white rounded hover:bg-forest-50 transition-colors"
              title="Copy Stream Key"
            >
              <Copy className="w-3 h-3 text-forest-600" />
              {copied === 'key' ? (
                <span className="text-sage-500 font-medium">Copied!</span>
              ) : (
                <span className="text-forest-600">Copy</span>
              )}
            </button>
          </div>
          <p className="text-xs font-mono text-forest-700 bg-white rounded px-2 py-1 break-all">
            {stream.stream_key}
          </p>
        </div>
        
        <div className="bg-forest-50 border border-forest-200 rounded p-2">
          <p className="text-xs text-forest-600">
            <strong>OBS Setup:</strong> Use both the Server URL and Stream Key above in your OBS settings.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-xs text-sage-500 hover:text-forest-600"
        >
          {showDetails ? 'Hide' : 'Show'} Details
        </button>
        
        <div className="flex items-center space-x-2">
          {stream.status === 'waiting' && (
            <button
              onClick={handleStart}
              disabled={isLoading}
              className="p-1.5 rounded hover:bg-sage-50 text-sage-500 disabled:opacity-50"
              title="Start receiving stream"
            >
              <Play className="w-4 h-4" />
            </button>
          )}

          {stream.status === 'live' && (
            <button
              onClick={handleStop}
              disabled={isLoading}
              className="p-1.5 rounded hover:bg-amber-50 text-amber-600 disabled:opacity-50"
              title="Stop stream"
            >
              <Square className="w-4 h-4" />
            </button>
          )}
          
          {stream.status !== 'live' && (
            <button
              onClick={handleDelete}
              disabled={isLoading}
              className="p-1.5 rounded hover:bg-red-50 text-red-600 disabled:opacity-50"
              title="Delete stream"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default StreamCard