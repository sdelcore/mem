import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { ChevronLeft, ChevronRight, Image, FileText, Tag, Clock, X, Maximize, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'

interface ContentItem {
  id: string
  timestamp: Date
  frame?: {
    url: string
    hash?: string
  }
  transcript?: string
  annotations?: string[]
}

interface ContentGroup {
  startIndex: number
  endIndex: number
  timestamp: Date
  frame?: {
    url: string
    hash?: string
  }
  transcript?: string
  annotations?: string[]
}

interface ContentViewerProps {
  startTime: Date
  endTime?: Date
  data?: any[]
}

const ContentViewer: React.FC<ContentViewerProps> = ({
  startTime,
  endTime,
  data = [],
}) => {
  const [contentItems, setContentItems] = useState<ContentItem[]>([])
  const [contentGroups, setContentGroups] = useState<ContentGroup[]>([])
  const [selectedGroupIndex, setSelectedGroupIndex] = useState(0)
  const [imageError, setImageError] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

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
      .map((item) => ({
        id: item.id || Math.random().toString(),
        timestamp: new Date(item.timestamp),
        frame: item.frame,
        transcript: item.transcript,
        annotations: item.annotations,
      }))
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())

    // Apply last frame tracking - fill in missing frames with the most recent frame
    let lastFrame: ContentItem['frame'] = undefined
    for (let i = 0; i < transformed.length; i++) {
      if (transformed[i].frame) {
        lastFrame = transformed[i].frame
      } else if (lastFrame) {
        // Use the last known frame if current timestamp has no frame
        transformed[i].frame = lastFrame
      }
    }

    // Group consecutive items with identical content
    const groups: ContentGroup[] = []
    if (transformed.length > 0) {
      let currentGroup: ContentGroup = {
        startIndex: 0,
        endIndex: 0,
        timestamp: transformed[0].timestamp,
        frame: transformed[0].frame,
        transcript: transformed[0].transcript,
        annotations: transformed[0].annotations,
      }

      for (let i = 1; i < transformed.length; i++) {
        const item = transformed[i]
        const prevItem = transformed[i - 1]
        
        // Check if content has changed
        const frameChanged = item.frame?.hash !== prevItem.frame?.hash
        const transcriptChanged = item.transcript !== prevItem.transcript
        
        if (frameChanged || transcriptChanged) {
          // Save current group and start a new one
          currentGroup.endIndex = i - 1
          groups.push(currentGroup)
          
          currentGroup = {
            startIndex: i,
            endIndex: i,
            timestamp: item.timestamp,
            frame: item.frame,
            transcript: item.transcript,
            annotations: item.annotations,
          }
        } else {
          // Extend current group
          currentGroup.endIndex = i
        }
      }
      
      // Don't forget the last group
      groups.push(currentGroup)
    }

    setContentItems(transformed)
    setContentGroups(groups)
    setSelectedGroupIndex(0)
    setImageError(null)
  }, [startTime, endTime, data])

  // Get current item based on content groups
  const currentGroup = contentGroups[selectedGroupIndex]
  const currentItem = currentGroup ? {
    id: contentItems[currentGroup.startIndex]?.id || '',
    timestamp: currentGroup.timestamp,
    frame: currentGroup.frame,
    transcript: currentGroup.transcript,
    annotations: currentGroup.annotations,
  } : contentItems[0]

  const handlePrevious = () => {
    setSelectedGroupIndex((prev) => Math.max(0, prev - 1))
    setImageError(null)
  }

  const handleNext = () => {
    setSelectedGroupIndex((prev) => Math.min(contentGroups.length - 1, prev + 1))
    setImageError(null)
  }

  const handleImageError = () => {
    setImageError('Failed to load image')
  }

  const handleImageClick = () => {
    if (currentItem?.frame && !imageError) {
      setIsFullscreen(true)
    }
  }

  const handleCloseFullscreen = () => {
    setIsFullscreen(false)
    setZoomLevel(1)
    setImagePosition({ x: 0, y: 0 })
  }

  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 0.25, 3))
  }

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 0.25, 0.5))
  }

  const handleZoomReset = () => {
    setZoomLevel(1)
    setImagePosition({ x: 0, y: 0 })
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    setZoomLevel(prev => Math.min(Math.max(prev + delta, 0.5), 3))
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

  // Handle ESC key to close fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false)
      }
    }

    if (isFullscreen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isFullscreen])

  if (contentGroups.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <Clock className="w-12 h-12 mx-auto mb-2 text-gray-400" />
          <p>No content available for this time range</p>
          <p className="text-sm mt-1">
            {format(startTime, 'HH:mm:ss')}
            {endTime && ` - ${format(endTime, 'HH:mm:ss')}`}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Navigation header */}
      <div className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
        <button
          onClick={handlePrevious}
          disabled={selectedGroupIndex === 0}
          className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Content {selectedGroupIndex + 1} of {contentGroups.length}
          </p>
          <p className="text-lg font-medium">
            {currentItem && format(currentItem.timestamp, 'HH:mm:ss')}
          </p>
          {currentGroup && currentGroup.startIndex !== currentGroup.endIndex && (
            <p className="text-xs text-gray-500">
              ({currentGroup.endIndex - currentGroup.startIndex + 1} timestamps)
            </p>
          )}
        </div>

        <button
          onClick={handleNext}
          disabled={selectedGroupIndex === contentGroups.length - 1}
          className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {currentItem && (
        <div className="space-y-4">
          {/* Frame/Image */}
          {currentItem.frame && (
            <div className="bg-gray-100 rounded-lg overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 bg-gray-200">
                <Image className="w-4 h-4 text-gray-600" />
                <span className="text-sm font-medium text-gray-700">Frame</span>
              </div>
              <div className="p-4">
                {imageError ? (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    <div className="text-center">
                      <Image className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                      <p>{imageError}</p>
                    </div>
                  </div>
                ) : (
                  <div className="relative group">
                    <img
                      src={currentItem.frame.url}
                      alt={`Frame at ${format(currentItem.timestamp, 'HH:mm:ss')}`}
                      onError={handleImageError}
                      onClick={handleImageClick}
                      className="w-full h-auto rounded-md border border-cream-100 cursor-pointer transition-opacity group-hover:opacity-90"
                    />
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      <div className="bg-black bg-opacity-50 rounded-full p-3">
                        <Maximize className="w-6 h-6 text-white" />
                      </div>
                    </div>
                  </div>
                )}
                {currentItem.frame.hash && (
                  <p className="text-xs text-gray-500 mt-2">
                    Hash: {currentItem.frame.hash}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Transcript */}
          {currentItem.transcript && (
            <div className="bg-green-50 rounded-lg overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 bg-green-100">
                <FileText className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-green-700">
                  Transcript
                </span>
              </div>
              <div className="p-4">
                <p className="text-gray-800 whitespace-pre-wrap">
                  {currentItem.transcript}
                </p>
              </div>
            </div>
          )}

          {/* Annotations */}
          {currentItem.annotations && currentItem.annotations.length > 0 && (
            <div className="bg-orange-50 rounded-lg overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 bg-orange-100">
                <Tag className="w-4 h-4 text-orange-600" />
                <span className="text-sm font-medium text-orange-700">
                  Annotations
                </span>
              </div>
              <div className="p-4">
                <ul className="space-y-2">
                  {currentItem.annotations.map((annotation, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-orange-500 mt-1">•</span>
                      <span className="text-gray-800">{annotation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Content type indicators */}
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-1">
          <div
            className={`w-3 h-3 rounded-full ${
              currentItem?.frame ? 'bg-blue-500' : 'bg-gray-300'
            }`}
          />
          <span>Frame</span>
        </div>
        <div className="flex items-center gap-1">
          <div
            className={`w-3 h-3 rounded-full ${
              currentItem?.transcript ? 'bg-green-500' : 'bg-gray-300'
            }`}
          />
          <span>Transcript</span>
        </div>
        <div className="flex items-center gap-1">
          <div
            className={`w-3 h-3 rounded-full ${
              currentItem?.annotations?.length ? 'bg-orange-500' : 'bg-gray-300'
            }`}
          />
          <span>Annotations</span>
        </div>
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && currentItem?.frame && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-95 flex items-center justify-center p-4"
          onClick={handleCloseFullscreen}
        >
          {/* Close button */}
          <button
            className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
            onClick={handleCloseFullscreen}
            aria-label="Close fullscreen"
          >
            <X className="w-8 h-8" />
          </button>
          
          {/* Zoom controls */}
          <div className="absolute top-4 left-4 flex items-center gap-2 bg-black bg-opacity-50 rounded-lg p-2 z-10">
            <button
              className="text-white hover:text-gray-300 transition-colors p-2 rounded hover:bg-white hover:bg-opacity-10"
              onClick={(e) => {
                e.stopPropagation()
                handleZoomOut()
              }}
              aria-label="Zoom out"
            >
              <ZoomOut className="w-5 h-5" />
            </button>
            
            <span className="text-white text-sm font-medium min-w-[60px] text-center">
              {Math.round(zoomLevel * 100)}%
            </span>
            
            <button
              className="text-white hover:text-gray-300 transition-colors p-2 rounded hover:bg-white hover:bg-opacity-10"
              onClick={(e) => {
                e.stopPropagation()
                handleZoomIn()
              }}
              aria-label="Zoom in"
            >
              <ZoomIn className="w-5 h-5" />
            </button>
            
            <div className="w-px h-6 bg-gray-600 mx-1" />
            
            <button
              className="text-white hover:text-gray-300 transition-colors p-2 rounded hover:bg-white hover:bg-opacity-10"
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
              src={currentItem.frame.url}
              alt={`Frame at ${format(currentItem.timestamp, 'HH:mm:ss')}`}
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
              {format(currentItem.timestamp, 'HH:mm:ss')}
            </p>
            <p className="text-sm text-gray-300 mt-1">
              Scroll to zoom • {zoomLevel > 1 ? 'Drag to pan • ' : ''}Press ESC or click outside to close
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default ContentViewer