import React from 'react'

interface TimelineSegmentProps {
  segment: {
    hasFrame: boolean
    hasTranscript: boolean
    hasAnnotation: boolean
    data: any[]
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
    </div>
  )
}

export default TimelineSegment