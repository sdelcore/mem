import { useState } from 'react'
import { format } from 'date-fns'
import { ChevronLeft, ChevronRight, Image, FileText, Tag, Layers, Circle } from 'lucide-react'
import PreviewTooltip from './PreviewTooltip'
import TimelineSegment from './TimelineSegment'

interface TimelineProps {
  startTime: Date
  endTime: Date
  data?: any[]
  onTimeSelect?: (time: Date) => void
  onRangeSelect?: (start: Date, end: Date) => void
  onNavigatePrevious?: () => void
  onNavigateNext?: () => void
}

const Timeline: React.FC<TimelineProps> = ({
  startTime,
  endTime,
  data = [],
  onTimeSelect,
  onRangeSelect,
  onNavigatePrevious,
  onNavigateNext,
}) => {
  const [hoveredSegment, setHoveredSegment] = useState<any>(null)
  const [isSelecting, setIsSelecting] = useState(false)
  const [selectionStart, setSelectionStart] = useState<Date | null>(null)
  const [selectionEnd, setSelectionEnd] = useState<Date | null>(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })

  // Group data by time segments (30-minute intervals)
  const segmentDuration = 30 * 60 * 1000 // 30 minutes in milliseconds
  const totalDuration = endTime.getTime() - startTime.getTime()
  const segmentCount = Math.ceil(totalDuration / segmentDuration)

  const segments = Array.from({ length: segmentCount }, (_, i) => {
    const segmentStart = new Date(startTime.getTime() + i * segmentDuration)
    const segmentEnd = new Date(Math.min(segmentStart.getTime() + segmentDuration, endTime.getTime()))
    
    // Find data within this segment
    const segmentData = data.filter(item => {
      const itemTime = new Date(item.timestamp).getTime()
      return itemTime >= segmentStart.getTime() && itemTime < segmentEnd.getTime()
    })

    const hasFrame = segmentData.some(item => item.frame)
    const hasTranscript = segmentData.some(item => item.transcript)
    const hasAnnotation = segmentData.some(item => item.annotations?.length > 0)
    
    // Track unique sources in this segment
    const uniqueSources = new Set(segmentData.map(item => item.source_id))
    const sourceCount = uniqueSources.size

    return {
      start: segmentStart,
      end: segmentEnd,
      hasFrame,
      hasTranscript,
      hasAnnotation,
      data: segmentData,
      sourceCount,
      sources: Array.from(uniqueSources),
    }
  })

  const handleSegmentClick = (segment: any) => {
    if (!isSelecting && onTimeSelect) {
      onTimeSelect(segment.start)
    }
  }

  const handleMouseDown = (_e: React.MouseEvent, segment: any) => {
    setIsSelecting(true)
    setSelectionStart(segment.start)
    setSelectionEnd(segment.start)
  }

  const handleMouseMove = (e: React.MouseEvent, segment: any) => {
    // Get the timeline container element
    const timelineContainer = document.querySelector('.timeline-container')
    if (timelineContainer) {
      const containerRect = timelineContainer.getBoundingClientRect()
      // Calculate position relative to timeline container
      const x = e.clientX - containerRect.left
      const y = -40 // Fixed position above the timeline
      setTooltipPosition({ x, y })
    }
    
    if (isSelecting && selectionStart) {
      setSelectionEnd(segment.end)
    }
    setHoveredSegment(segment)
  }

  const handleMouseUp = () => {
    if (isSelecting && selectionStart && selectionEnd && onRangeSelect) {
      const start = selectionStart < selectionEnd ? selectionStart : selectionEnd
      const end = selectionStart < selectionEnd ? selectionEnd : selectionStart
      onRangeSelect(start, end)
    }
    setIsSelecting(false)
  }

  const handleMouseLeave = () => {
    setHoveredSegment(null)
    if (isSelecting) {
      setIsSelecting(false)
    }
  }

  const getSegmentColor = (segment: any) => {
    if (segment.hasFrame && segment.hasTranscript) return 'bg-forest-500'
    if (segment.hasFrame) return 'bg-forest-300'
    if (segment.hasTranscript) return 'bg-sage-300'
    if (segment.hasAnnotation) return 'bg-sage-400'
    return 'bg-cream-200'
  }

  const isInSelection = (segment: any) => {
    if (!isSelecting || !selectionStart || !selectionEnd) return false
    const start = selectionStart < selectionEnd ? selectionStart : selectionEnd
    const end = selectionStart < selectionEnd ? selectionEnd : selectionStart
    return segment.start >= start && segment.end <= end
  }

  return (
    <div className="relative">
      {/* Time labels - responsive */}
      <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-0 text-xs font-medium text-forest-600 mb-3">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-sage-300 animate-pulse"></div>
          <span>{format(startTime, 'MMM dd, HH:mm:ss')}</span>
        </div>
        <span className="text-sage-400 hidden sm:block">Duration: {Math.round((endTime.getTime() - startTime.getTime()) / (1000 * 60))} min</span>
        <span className="text-sage-400">{format(endTime, 'HH:mm:ss')}</span>
      </div>

      {/* Drag hint - hidden on mobile */}
      <p className="text-xs text-sage-400 mb-2 hidden sm:block">
        Tip: Click to select time, drag to select range
      </p>

      {/* Timeline with navigation */}
      <div className="relative flex items-center gap-2">
        {/* Left Navigation Arrow - touch friendly */}
        {onNavigatePrevious && (
          <button
            onClick={onNavigatePrevious}
            className="flex-shrink-0 w-11 h-11 min-w-11 min-h-11 flex items-center justify-center bg-forest-500 hover:bg-forest-600 text-cream-100 rounded-lg transition-colors duration-150"
            aria-label="Previous time period"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
        )}

        {/* Timeline segments - responsive height */}
        <div
          className="timeline-container flex-1 relative h-24 sm:h-32 bg-cream-50 rounded-lg overflow-hidden cursor-pointer timeline-scrollbar border border-cream-200"
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        >
          <div className="flex h-full">
            {segments.map((segment, index) => (
              <div
                key={index}
                className={`flex-1 border-r border-cream-300/50 transition-all hover:bg-white/40 ${
                  isInSelection(segment) ? 'ring-2 ring-sage-300 bg-sage-50/30' : ''
                }`}
                onMouseDown={(e) => handleMouseDown(e, segment)}
                onMouseMove={(e) => handleMouseMove(e, segment)}
                onClick={() => handleSegmentClick(segment)}
              >
                <TimelineSegment
                  segment={segment}
                  color={getSegmentColor(segment)}
                  isHovered={hoveredSegment === segment}
                />
              </div>
            ))}
          </div>

        {/* Selection overlay */}
        {isSelecting && selectionStart && selectionEnd && (
          <div 
            className="absolute top-0 h-full bg-sage-200 bg-opacity-30 pointer-events-none"
            style={{
              left: `${(Math.min(selectionStart.getTime(), selectionEnd.getTime()) - startTime.getTime()) / totalDuration * 100}%`,
              width: `${Math.abs(selectionEnd.getTime() - selectionStart.getTime()) / totalDuration * 100}%`,
            }}
          />
        )}
        </div>
        
        {/* Right Navigation Arrow - touch friendly */}
        {onNavigateNext && (
          <button
            onClick={onNavigateNext}
            className="flex-shrink-0 w-11 h-11 min-w-11 min-h-11 flex items-center justify-center bg-forest-500 hover:bg-forest-600 text-cream-100 rounded-lg transition-colors duration-150"
            aria-label="Next time period"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        )}
      </div>

      {/* Hover tooltip */}
      {hoveredSegment && (
        <PreviewTooltip
          visible={true}
          x={tooltipPosition.x}
          y={tooltipPosition.y}
          timestamp={hoveredSegment.start}
          hasFrame={hoveredSegment.hasFrame}
          hasTranscript={hoveredSegment.hasTranscript}
          hasAnnotation={hoveredSegment.hasAnnotation}
          frameUrl={hoveredSegment.data?.[0]?.frame?.url}
        />
      )}

      {/* Legend - responsive grid on mobile */}
      <div className="grid grid-cols-2 sm:flex sm:flex-wrap items-center gap-2 sm:gap-3 mt-4 sm:mt-6 p-3 bg-cream-50 rounded-md border border-cream-200" role="group" aria-label="Content type legend">
        <span className="text-xs font-medium text-forest-600 uppercase tracking-wider col-span-2 sm:col-span-1 mb-1 sm:mb-0">Legend:</span>
        <div className="flex items-center gap-1.5">
          <Circle className="w-3 h-3 text-cream-300" />
          <div className="w-3 h-3 bg-cream-200 rounded-full shadow-sm"></div>
          <span className="text-xs text-forest-600">No data</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Image className="w-3 h-3 text-forest-300" />
          <div className="w-3 h-3 bg-forest-300 rounded-full shadow-sm"></div>
          <span className="text-xs text-forest-600">Frames</span>
        </div>
        <div className="flex items-center gap-1.5">
          <FileText className="w-3 h-3 text-sage-300" />
          <div className="w-3 h-3 bg-sage-300 rounded-full shadow-sm"></div>
          <span className="text-xs text-forest-600">Transcripts</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Layers className="w-3 h-3 text-forest-500" />
          <div className="w-3 h-3 bg-forest-500 rounded-full shadow-sm"></div>
          <span className="text-xs text-forest-600">Both</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Tag className="w-3 h-3 text-sage-400" />
          <div className="w-3 h-3 bg-sage-400 rounded-full shadow-sm"></div>
          <span className="text-xs text-forest-600">Annotations</span>
        </div>
      </div>
    </div>
  )
}

export default Timeline