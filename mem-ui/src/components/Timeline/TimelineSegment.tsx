import React from 'react'

interface TimelineSegmentProps {
  segment: {
    hasFrame: boolean
    hasTranscript: boolean
    hasAnnotation: boolean
    data: any[]
    sourceCount?: number
    sources?: number[]
  }
  color: string
  isHovered: boolean
}

const TimelineSegment: React.FC<TimelineSegmentProps> = ({
  segment,
  color,
  isHovered,
}) => {
  const getHeight = () => {
    const dataCount = segment.data.length
    if (dataCount === 0) return '20%'
    if (dataCount < 5) return '40%'
    if (dataCount < 10) return '60%'
    if (dataCount < 20) return '80%'
    return '100%'
  }

  return (
    <div className="relative h-full flex items-end">
      <div
        className={`w-full transition-all duration-200 ${color} ${
          isHovered ? 'opacity-100' : 'opacity-70'
        }`}
        style={{
          height: getHeight(),
          boxShadow: isHovered ? '0 0 10px rgba(0,0,0,0.2)' : 'none',
        }}
      />
      {/* Show indicator for multiple sources */}
      {segment.sourceCount && segment.sourceCount > 1 && (
        <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
          {segment.sourceCount}
        </div>
      )}
    </div>
  )
}

export default TimelineSegment