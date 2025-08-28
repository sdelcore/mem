import React, { useState, useRef, useEffect } from 'react'
import { format } from 'date-fns'

interface VerticalActivityTimelineProps {
  selectedDate: Date
  onTimeSelect: (time: Date) => void
  onRangeSelect?: (start: Date, end: Date) => void
  data?: any[]
  currentTime?: Date
}

interface HourData {
  hour: number
  count: number
  hasFrame: boolean
  hasTranscript: boolean
  hasAnnotation: boolean
}

const VerticalActivityTimeline: React.FC<VerticalActivityTimelineProps> = ({
  selectedDate,
  onTimeSelect,
  onRangeSelect,
  data = [],
  currentTime = new Date(),
}) => {
  const [hoveredHour, setHoveredHour] = useState<number | null>(null)
  const [isSelecting, setIsSelecting] = useState(false)
  const [selectionStart, setSelectionStart] = useState<number | null>(null)
  const [selectionEnd, setSelectionEnd] = useState<number | null>(null)
  const timelineRef = useRef<HTMLDivElement>(null)

  // Process data to get activity per hour
  const processHourlyData = (): HourData[] => {
    const hourlyData: HourData[] = []
    
    for (let hour = 0; hour < 24; hour++) {
      const hourStart = new Date(selectedDate)
      hourStart.setHours(hour, 0, 0, 0)
      const hourEnd = new Date(selectedDate)
      hourEnd.setHours(hour, 59, 59, 999)

      const hourItems = data.filter(item => {
        const itemTime = new Date(item.timestamp)
        return itemTime >= hourStart && itemTime <= hourEnd
      })

      hourlyData.push({
        hour,
        count: hourItems.length,
        hasFrame: hourItems.some(item => item.frame),
        hasTranscript: hourItems.some(item => item.transcript),
        hasAnnotation: hourItems.some(item => item.annotations?.length > 0),
      })
    }

    return hourlyData
  }

  const hourlyData = processHourlyData()
  const maxCount = Math.max(...hourlyData.map(h => h.count), 1)

  // Check if current time is today
  const isToday = format(selectedDate, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')
  const currentHour = currentTime.getHours()
  const currentMinutes = currentTime.getMinutes()

  const handleHourClick = (hour: number) => {
    const clickTime = new Date(selectedDate)
    clickTime.setHours(hour, 30, 0, 0) // Set to middle of the hour
    onTimeSelect(clickTime)
  }

  const handleMouseDown = (hour: number) => {
    setIsSelecting(true)
    setSelectionStart(hour)
    setSelectionEnd(hour)
  }

  const handleMouseMove = (hour: number) => {
    if (isSelecting && selectionStart !== null) {
      setSelectionEnd(hour)
    }
    setHoveredHour(hour)
  }

  const handleMouseUp = () => {
    if (isSelecting && selectionStart !== null && selectionEnd !== null && onRangeSelect) {
      const startHour = Math.min(selectionStart, selectionEnd)
      const endHour = Math.max(selectionStart, selectionEnd)
      
      const rangeStart = new Date(selectedDate)
      rangeStart.setHours(startHour, 0, 0, 0)
      
      const rangeEnd = new Date(selectedDate)
      rangeEnd.setHours(endHour, 59, 59, 999)
      
      onRangeSelect(rangeStart, rangeEnd)
    }
    setIsSelecting(false)
  }

  const handleMouseLeave = () => {
    setHoveredHour(null)
    if (isSelecting) {
      setIsSelecting(false)
    }
  }

  const isInSelection = (hour: number) => {
    if (!isSelecting || selectionStart === null || selectionEnd === null) return false
    const start = Math.min(selectionStart, selectionEnd)
    const end = Math.max(selectionStart, selectionEnd)
    return hour >= start && hour <= end
  }

  const getActivityColor = (data: HourData) => {
    if (data.hasFrame && data.hasTranscript) return 'bg-forest-500'
    if (data.hasFrame) return 'bg-forest-300'
    if (data.hasTranscript) return 'bg-sage-300'
    if (data.hasAnnotation) return 'bg-sage-400'
    if (data.count > 0) return 'bg-sage-200'
    return 'bg-forest-700'
  }

  // Auto-scroll to current hour on mount if today
  useEffect(() => {
    if (isToday && timelineRef.current) {
      const hourElement = timelineRef.current.querySelector(`[data-hour="${currentHour}"]`)
      if (hourElement && typeof hourElement.scrollIntoView === 'function') {
        hourElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [isToday, currentHour])

  return (
    <div 
      ref={timelineRef}
      className="relative h-full"
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
    >
      {/* Hours */}
      {Array.from({ length: 24 }, (_, hour) => {
        const data = hourlyData[hour]
        const activityWidth = (data.count / maxCount) * 100

        return (
          <div
            key={hour}
            data-hour={hour}
            className={`
              relative h-12 border-b border-forest-500 cursor-pointer transition-all
              ${hoveredHour === hour ? 'bg-forest-500/20' : ''}
              ${isInSelection(hour) ? 'bg-sage-300/20' : ''}
            `}
            onMouseDown={() => handleMouseDown(hour)}
            onMouseMove={() => handleMouseMove(hour)}
            onClick={() => handleHourClick(hour)}
          >
            {/* Hour label */}
            <div className="absolute left-2 top-1/2 -translate-y-1/2 text-cream-200 text-sm font-medium">
              {hour.toString().padStart(2, '0')}:00
            </div>

            {/* Activity bar */}
            <div className="absolute right-2 top-1/2 -translate-y-1/2 w-32 h-6">
              <div className="relative h-full bg-forest-700/50 rounded">
                <div
                  className={`absolute left-0 top-0 h-full rounded transition-all ${getActivityColor(data)}`}
                  style={{ width: `${activityWidth}%` }}
                />
                {data.count > 0 && (
                  <span className="absolute right-1 top-1/2 -translate-y-1/2 text-xs text-cream-100 font-medium">
                    {data.count}
                  </span>
                )}
              </div>
            </div>

            {/* Current time marker */}
            {isToday && hour === currentHour && (
              <div 
                className="absolute left-0 w-full h-0.5 bg-red-500"
                style={{ 
                  top: `${(currentMinutes / 60) * 100}%`,
                  boxShadow: '0 0 8px rgba(239, 68, 68, 0.5)'
                }}
              >
                <div className="absolute -left-1 -top-1 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              </div>
            )}

            {/* Hover tooltip */}
            {hoveredHour === hour && data.count > 0 && (
              <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-10 bg-forest-700 text-cream-100 px-2 py-1 rounded text-xs whitespace-nowrap">
                {data.count} activities
                {data.hasFrame && ' • Frames'}
                {data.hasTranscript && ' • Transcripts'}
                {data.hasAnnotation && ' • Annotations'}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default VerticalActivityTimeline