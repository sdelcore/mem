import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { ChevronRight, Tag, Clock, X, Maximize, ZoomIn, ZoomOut, RotateCcw, Plus } from 'lucide-react'
import AddContentModal from './AddContentModal'
import SpeakerEditor from './SpeakerEditor'

interface Annotation {
  annotation_id?: number
  annotation_type?: string
  content: string
  metadata?: {
    speaker?: string
    duration?: number
  }
  created_by?: string
  created_at?: string
}

interface ContentItem {
  id: string
  timestamp: Date
  source_id?: number
  source_location?: string
  source_type?: string
  transcription_id?: number
  frame?: {
    url: string
    hash?: string
    source_id?: number
  }
  transcript?: string
  speaker_name?: string
  speaker_confidence?: number
  annotations?: Annotation[]
}

interface TimeChunk {
  id: string
  startTime: Date
  endTime: Date
  items: ContentItem[]
  hasFrames: boolean
  hasTranscripts: boolean
  hasAnnotations: boolean
  frameCount: number
  transcriptCount: number
}

const CHUNK_DURATION_MS = 30 * 60 * 1000
const ZOOM = { MIN: 0.5, MAX: 3, STEP: 0.25, WHEEL_STEP: 0.1 }

const groupIntoChunks = (items: ContentItem[]): TimeChunk[] => {
  if (items.length === 0) return []

  const sortedItems = [...items].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
  const chunkMap = new Map<number, ContentItem[]>()

  sortedItems.forEach(item => {
    const itemTime = item.timestamp.getTime()
    const chunkStart = Math.floor(itemTime / CHUNK_DURATION_MS) * CHUNK_DURATION_MS
    if (!chunkMap.has(chunkStart)) {
      chunkMap.set(chunkStart, [])
    }
    chunkMap.get(chunkStart)!.push(item)
  })

  const chunks: TimeChunk[] = []
  chunkMap.forEach((chunkItems, chunkStartMs) => {
    chunks.push({
      id: `chunk-${chunkStartMs}`,
      startTime: new Date(chunkStartMs),
      endTime: new Date(chunkStartMs + CHUNK_DURATION_MS),
      items: chunkItems,
      hasFrames: chunkItems.some(item => item.frame),
      hasTranscripts: chunkItems.some(item => item.transcript),
      hasAnnotations: chunkItems.some(item => item.annotations && item.annotations.length > 0),
      frameCount: chunkItems.filter(item => item.frame).length,
      transcriptCount: chunkItems.filter(item => item.transcript).length,
    })
  })

  return chunks.sort((a, b) => a.startTime.getTime() - b.startTime.getTime())
}

interface RawContentData {
  id?: string
  timestamp: string | Date
  source_id?: number
  source_location?: string
  source_type?: string
  transcription_id?: number
  frame?: { url: string; hash?: string; source_id?: number }
  transcript?: string
  speaker_name?: string
  speaker_confidence?: number
  annotations?: Annotation[] | string[]
}

interface ContentViewerProps {
  startTime: Date
  endTime?: Date
  data?: RawContentData[]
}

const ContentViewer: React.FC<ContentViewerProps> = ({
  startTime,
  endTime,
  data = [],
}) => {
  const [contentItems, setContentItems] = useState<ContentItem[]>([])
  const [timeChunks, setTimeChunks] = useState<TimeChunk[]>([])
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set())
  const [fullscreenItem, setFullscreenItem] = useState<ContentItem | null>(null)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedChunkTime, setSelectedChunkTime] = useState<Date | null>(null)

  useEffect(() => {
    // Filter data within the time range
    const filtered = data.filter((item) => {
      const itemTime = new Date(item.timestamp)
      if (endTime) {
        return itemTime >= startTime && itemTime <= endTime
      }
      // For single time point, show content within 5 minutes
      const rangeEnd = new Date(startTime.getTime() + 5 * 60 * 1000)
      return itemTime >= startTime && itemTime < rangeEnd
    })

    // Transform and sort by timestamp
    const transformed: ContentItem[] = filtered
      .map((item) => {
        // Normalize annotations - convert strings to Annotation objects
        const annotations = item.annotations?.map((a: Annotation | string) =>
          typeof a === 'string' ? { content: a } : a
        )
        return {
          id: item.id || Math.random().toString(),
          timestamp: new Date(item.timestamp),
          source_id: item.source_id,
          source_location: item.source_location,
          source_type: item.source_type,
          transcription_id: item.transcription_id,
          frame: item.frame,
          transcript: item.transcript,
          speaker_name: item.speaker_name,
          speaker_confidence: item.speaker_confidence,
          annotations,
        }
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())

    // Fill in missing frames with the most recent frame
    let lastFrame: ContentItem['frame'] = undefined
    for (let i = 0; i < transformed.length; i++) {
      if (transformed[i].frame) lastFrame = transformed[i].frame
      else if (lastFrame) transformed[i].frame = lastFrame
    }
    const chunks = groupIntoChunks(transformed)

    setContentItems(transformed)
    setTimeChunks(chunks)
  }, [startTime, endTime, data])

  const toggleChunk = (chunkId: string) => {
    setExpandedChunks(prev => {
      const next = new Set(prev)
      next.has(chunkId) ? next.delete(chunkId) : next.add(chunkId)
      return next
    })
  }

  const expandAllChunks = () => {
    setExpandedChunks(new Set(timeChunks.map(c => c.id)))
  }

  const collapseAllChunks = () => {
    setExpandedChunks(new Set())
  }

  const handleImageClick = (item: ContentItem) => {
    if (item?.frame) {
      setFullscreenItem(item)
    }
  }

  const handleCloseFullscreen = () => {
    setFullscreenItem(null)
    setZoomLevel(1)
    setImagePosition({ x: 0, y: 0 })
  }

  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + ZOOM.STEP, ZOOM.MAX))
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - ZOOM.STEP, ZOOM.MIN))
  const handleZoomReset = () => { setZoomLevel(1); setImagePosition({ x: 0, y: 0 }) }

  const handleOpenAddModal = (chunkTime: Date, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedChunkTime(chunkTime)
    setModalOpen(true)
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -ZOOM.WHEEL_STEP : ZOOM.WHEEL_STEP
    setZoomLevel(prev => Math.min(Math.max(prev + delta, ZOOM.MIN), ZOOM.MAX))
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoomLevel > 1) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - imagePosition.x, y: e.clientY - imagePosition.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoomLevel > 1) {
      setImagePosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleCloseFullscreen()
    }
    if (fullscreenItem) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [fullscreenItem])

  if (timeChunks.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-sage-400">
        <div className="text-center p-8">
          <Clock className="w-12 h-12 mx-auto mb-3 text-cream-300" />
          <p className="text-forest-600 font-medium mb-2">No content in this time range</p>
          <p className="text-sage-400 text-sm mb-1">
            {format(startTime, 'HH:mm:ss')}
            {endTime && ` - ${format(endTime, 'HH:mm:ss')}`}
          </p>
          <p className="text-sage-400 text-xs">
            Try expanding the view or navigate to a different time period.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Expand/Collapse All Controls */}
      <div className="flex items-center justify-between bg-cream-50 p-3 rounded-lg">
        <p className="text-sm text-sage-500">
          {timeChunks.length} time period{timeChunks.length !== 1 ? 's' : ''} • {contentItems.length} total items
        </p>
        <div className="flex gap-2">
          <button
            onClick={expandAllChunks}
            className="text-xs text-forest-600 hover:text-forest-700 px-2 py-1 rounded hover:bg-cream-100 transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={collapseAllChunks}
            className="text-xs text-forest-600 hover:text-forest-700 px-2 py-1 rounded hover:bg-cream-100 transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Time Chunks */}
      {timeChunks.map(chunk => {
        const isExpanded = expandedChunks.has(chunk.id)
        return (
          <div key={chunk.id} className="rounded-lg overflow-hidden border border-cream-200">
            {/* Chunk Header */}
            <div className="flex items-center justify-between p-3 sm:p-4 bg-cream-100">
              <button
                onClick={() => toggleChunk(chunk.id)}
                aria-expanded={isExpanded}
                aria-controls={`chunk-content-${chunk.id}`}
                className="flex items-center gap-3 flex-1 hover:bg-cream-200 -m-2 p-2 rounded-lg transition-colors"
              >
                <ChevronRight className={`w-5 h-5 text-forest-600 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
                <div className="text-left">
                  <p className="font-medium text-forest-700">
                    {format(chunk.startTime, 'HH:mm')} - {format(chunk.endTime, 'HH:mm')}
                  </p>
                  <p className="text-xs text-sage-400">
                    {chunk.frameCount} frame{chunk.frameCount !== 1 ? 's' : ''}, {chunk.transcriptCount} transcript{chunk.transcriptCount !== 1 ? 's' : ''}
                  </p>
                </div>
              </button>

              {/* Content type indicators and add button */}
              <div className="flex items-center gap-2">
                {chunk.hasFrames && (
                  <div className="w-3 h-3 rounded-full bg-forest-300" title="Has frames" />
                )}
                {chunk.hasTranscripts && (
                  <div className="w-3 h-3 rounded-full bg-sage-300" title="Has transcripts" />
                )}
                {chunk.hasAnnotations && (
                  <div className="w-3 h-3 rounded-full bg-sage-400" title="Has annotations" />
                )}
                <button
                  onClick={(e) => handleOpenAddModal(chunk.startTime, e)}
                  className="ml-2 p-1.5 rounded-lg bg-forest-100 hover:bg-forest-200 text-forest-600 transition-colors"
                  title="Add content to this time period"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Chunk Content */}
            <div
              id={`chunk-content-${chunk.id}`}
              className={`overflow-hidden transition-all duration-300 ease-in-out ${
                isExpanded ? 'max-h-[5000px] opacity-100' : 'max-h-0 opacity-0'
              }`}
            >
              <div className="space-y-3 p-3 sm:p-4 bg-cream-50 border-t border-cream-200">
                {chunk.items.map((item) => (
                  <div key={item.id} className={`flex gap-3 sm:gap-4 p-3 bg-white rounded-lg border border-cream-200 ${!item.frame ? 'border-l-4 border-l-sage-300' : ''}`}>
                    {/* Timestamp */}
                    <div className="flex-shrink-0 text-xs text-sage-400 w-14 sm:w-16 pt-1">
                      {format(item.timestamp, 'HH:mm:ss')}
                    </div>

                    {/* Frame (left side) - only render if frame exists */}
                    {item.frame && (
                      <div className="flex-shrink-0 w-24 sm:w-32 md:w-48">
                        <div className="relative group">
                          <img
                            src={item.frame.url}
                            alt={`Frame at ${format(item.timestamp, 'HH:mm:ss')}`}
                            onClick={() => handleImageClick(item)}
                            className="w-full h-auto rounded cursor-pointer hover:opacity-90 transition-opacity border border-cream-200"
                          />
                          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                            <div className="bg-black bg-opacity-50 rounded-full p-2">
                              <Maximize className="w-4 h-4 text-white" />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Transcript and annotations (right side) */}
                    <div className="flex-1 space-y-2 min-w-0">
                      {item.transcript && (
                        <p className="text-sm text-forest-700 break-words">
                          {item.transcription_id ? (
                            <SpeakerEditor
                              transcriptionId={item.transcription_id}
                              currentSpeaker={item.speaker_name || null}
                              speakerConfidence={item.speaker_confidence}
                            />
                          ) : (
                            <span className="font-semibold text-sage-600">
                              [{item.speaker_name || 'Unknown'}]
                            </span>
                          )}
                          {': '}{item.transcript}
                        </p>
                      )}

                      {/* Annotations */}
                      {item.annotations?.map((ann, i) => (
                        <div key={`ann-${i}`} className="text-xs text-sage-500 flex items-start gap-1">
                          <Tag className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <span className="break-words">{ann.content}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )
      })}

      {/* Fullscreen Modal */}
      {fullscreenItem?.frame && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-95 flex items-center justify-center p-4"
          onClick={handleCloseFullscreen}
        >
          {/* Close button - touch friendly */}
          <button
            className="absolute top-4 right-4 p-2.5 min-h-11 min-w-11 text-white hover:text-gray-300 transition-colors z-10 flex items-center justify-center"
            onClick={handleCloseFullscreen}
            aria-label="Close fullscreen"
          >
            <X className="w-8 h-8" />
          </button>

          {/* Zoom controls - touch friendly */}
          <div className="absolute top-4 left-4 flex items-center gap-1 sm:gap-2 bg-black bg-opacity-50 rounded-lg p-1.5 sm:p-2 z-10">
            <button
              className="text-white hover:text-gray-300 transition-colors p-2.5 min-h-11 min-w-11 rounded hover:bg-white hover:bg-opacity-10 flex items-center justify-center"
              onClick={(e) => {
                e.stopPropagation()
                handleZoomOut()
              }}
              aria-label="Zoom out"
            >
              <ZoomOut className="w-5 h-5" />
            </button>

            <span className="text-white text-xs sm:text-sm font-medium min-w-[50px] sm:min-w-[60px] text-center">
              {Math.round(zoomLevel * 100)}%
            </span>

            <button
              className="text-white hover:text-gray-300 transition-colors p-2.5 min-h-11 min-w-11 rounded hover:bg-white hover:bg-opacity-10 flex items-center justify-center"
              onClick={(e) => {
                e.stopPropagation()
                handleZoomIn()
              }}
              aria-label="Zoom in"
            >
              <ZoomIn className="w-5 h-5" />
            </button>

            <div className="w-px h-6 bg-gray-600 mx-1 hidden sm:block" />

            <button
              className="text-white hover:text-gray-300 transition-colors p-2.5 min-h-11 min-w-11 rounded hover:bg-white hover:bg-opacity-10 hidden sm:flex items-center justify-center"
              onClick={(e) => {
                e.stopPropagation()
                handleZoomReset()
              }}
              aria-label="Reset zoom"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
          </div>

          {/* Image container */}
          <div
            className="relative w-full h-full flex items-center justify-center"
            onClick={(e) => e.stopPropagation()}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{
              cursor: zoomLevel > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default'
            }}
          >
            <img
              src={fullscreenItem.frame.url}
              alt={`Frame at ${format(fullscreenItem.timestamp, 'HH:mm:ss')}`}
              className="max-w-full max-h-[90vh] object-contain select-none transition-transform duration-200"
              style={{
                transform: `scale(${zoomLevel}) translate(${imagePosition.x / zoomLevel}px, ${imagePosition.y / zoomLevel}px)`,
                transformOrigin: 'center'
              }}
              draggable={false}
            />
          </div>

          {/* Info overlay */}
          <div className="absolute bottom-4 left-4 text-white pointer-events-none">
            <p className="text-lg font-medium">
              {format(fullscreenItem.timestamp, 'HH:mm:ss')}
            </p>
            <p className="text-sm text-gray-300 mt-1">
              Scroll to zoom • {zoomLevel > 1 ? 'Drag to pan • ' : ''}Press ESC or click outside to close
            </p>
          </div>
        </div>
      )}

      {/* Add Content Modal */}
      <AddContentModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        timestamp={selectedChunkTime || new Date()}
        onContentCreated={() => {
          // Modal will close itself, timeline will refresh via query invalidation
        }}
      />
    </div>
  )
}

export default ContentViewer