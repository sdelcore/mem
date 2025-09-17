import React, { useState, useRef, useEffect } from 'react'
import { Camera, X, ChevronDown } from 'lucide-react'
import { useStreams } from '../../hooks/useStreams'
import StreamControls from './StreamControls'
import StreamCard from './StreamCard'

const StreamManager: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  // Fetch streams with polling when expanded
  const { data, isLoading, error, refetch } = useStreams(isExpanded ? 5000 : undefined)
  
  const activeCount = data?.streams.filter(s => s.status === 'live').length || 0
  const totalCount = data?.total_count || 0

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsExpanded(false)
      }
    }

    if (isExpanded) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [isExpanded])

  // Auto-expand if there are active streams
  useEffect(() => {
    if (activeCount > 0 && !isExpanded) {
      // Don't auto-expand, but show a subtle indicator
    }
  }, [activeCount])

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`
          flex items-center space-x-2 px-4 py-2 rounded-lg transition-all
          ${isExpanded 
            ? 'bg-forest-600 text-cream-50' 
            : 'bg-forest-500 text-cream-50 hover:bg-forest-600'
          }
        `}
      >
        <Camera className="w-5 h-5" />
        <span className="font-medium">Streams</span>
        
        {/* Active Stream Indicator */}
        {activeCount > 0 && (
          <span className="flex items-center space-x-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            <span className="text-xs font-bold">{activeCount}</span>
          </span>
        )}
        
        <ChevronDown 
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
        />
      </button>

      {/* Dropdown Panel */}
      {isExpanded && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-flat border border-cream-200 overflow-hidden z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-cream-50 border-b border-cream-200">
            <div className="flex items-center space-x-2">
              <Camera className="w-5 h-5 text-forest-500" />
              <h3 className="font-semibold text-forest-700">Stream Management</h3>
              {totalCount > 0 && (
                <span className="text-xs text-sage-500">
                  ({activeCount} active / {totalCount} total)
                </span>
              )}
            </div>
            <button
              onClick={() => setIsExpanded(false)}
              className="text-sage-400 hover:text-forest-600 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Create Stream Controls */}
          <StreamControls onStreamCreated={refetch} />

          {/* Stream List */}
          <div className="max-h-96 overflow-y-auto">
            {isLoading ? (
              <div className="p-8 text-center">
                <div className="w-8 h-8 border-3 border-forest-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-sm text-sage-500">Loading streams...</p>
              </div>
            ) : error ? (
              <div className="p-8 text-center">
                <p className="text-sm text-red-600 mb-2">Failed to load streams</p>
                <button
                  onClick={() => refetch()}
                  className="text-xs text-forest-600 hover:underline"
                >
                  Try again
                </button>
              </div>
            ) : !data?.streams?.length ? (
              <div className="p-8 text-center">
                <Camera className="w-12 h-12 text-cream-300 mx-auto mb-3" />
                <p className="text-sm text-sage-500 mb-1">No streams yet</p>
                <p className="text-xs text-sage-400">
                  Create a stream session to start receiving from OBS Studio
                </p>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {/* Active streams first */}
                {data.streams
                  .sort((a, b) => {
                    // Sort by status: live > waiting > ended > error
                    const statusOrder = { live: 0, waiting: 1, ended: 2, error: 3 }
                    return statusOrder[a.status] - statusOrder[b.status]
                  })
                  .map((stream) => (
                    <StreamCard
                      key={stream.stream_key}
                      stream={stream}
                      onRefresh={refetch}
                    />
                  ))}
              </div>
            )}
          </div>

          {/* Footer with instructions */}
          {data?.streams.length > 0 && (
            <div className="px-4 py-3 bg-cream-50 border-t border-cream-200">
              <p className="text-xs text-sage-500">
                Configure OBS Studio with the RTMP URL and Stream Key shown above.
                Click play to start receiving the stream.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default StreamManager