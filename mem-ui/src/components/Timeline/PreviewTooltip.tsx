import React, { useEffect, useState } from 'react'
import { format } from 'date-fns'

interface PreviewTooltipProps {
  visible: boolean
  x: number
  y: number
  timestamp: Date
  hasFrame?: boolean
  hasTranscript?: boolean
  hasAnnotation?: boolean
  frameUrl?: string
}

const PreviewTooltip: React.FC<PreviewTooltipProps> = ({
  visible,
  x,
  y,
  timestamp,
  hasFrame,
  hasTranscript,
  hasAnnotation,
  frameUrl,
}) => {
  const [adjustedX, setAdjustedX] = useState(x)

  useEffect(() => {
    if (!visible) return

    // Calculate tooltip boundaries
    const tooltipWidth = 200 // minWidth from style
    const padding = 20 // Padding from edges
    
    // Get container width (parent element width)
    const container = document.querySelector('.relative')
    const containerWidth = container?.clientWidth || window.innerWidth
    
    // Calculate left position with transform offset
    const leftPos = x - tooltipWidth / 2
    const rightPos = x + tooltipWidth / 2
    
    let newX = x
    
    // Check left boundary
    if (leftPos < padding) {
      newX = tooltipWidth / 2 + padding
    }
    // Check right boundary
    else if (rightPos > containerWidth - padding) {
      newX = containerWidth - tooltipWidth / 2 - padding
    }
    
    setAdjustedX(newX)
  }, [x, visible])

  if (!visible) return null

  return (
    <div
      className="absolute z-50 bg-white rounded-md shadow-flat-md p-3 pointer-events-none border border-cream-200"
      style={{
        left: `${adjustedX}px`,
        top: `${y}px`,
        transform: 'translateX(-50%)',
        minWidth: '200px',
        maxWidth: '250px',
      }}
    >
      {/* Timestamp */}
      <div className="text-sm font-semibold text-gray-900 mb-2">
        {format(timestamp, 'HH:mm:ss')}
      </div>

      {/* Frame preview */}
      {hasFrame && frameUrl && (
        <div className="mb-2">
          <img
            src={frameUrl}
            alt="Frame preview"
            className="w-full h-32 object-cover rounded"
          />
        </div>
      )}

      {/* Content indicators */}
      <div className="flex gap-2 text-xs">
        {hasFrame && (
          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
            Frame
          </span>
        )}
        {hasTranscript && (
          <span className="px-2 py-1 bg-green-100 text-green-700 rounded">
            Transcript
          </span>
        )}
        {hasAnnotation && (
          <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded">
            Annotation
          </span>
        )}
        {!hasFrame && !hasTranscript && !hasAnnotation && (
          <span className="text-gray-500">No content</span>
        )}
      </div>

      {/* Arrow pointing down */}
      <div
        className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full"
        style={{
          width: 0,
          height: 0,
          borderLeft: '8px solid transparent',
          borderRight: '8px solid transparent',
          borderTop: '8px solid white',
        }}
      />
    </div>
  )
}

export default PreviewTooltip