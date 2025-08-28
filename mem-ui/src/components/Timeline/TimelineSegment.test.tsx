import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import TimelineSegment from './TimelineSegment'

describe('TimelineSegment', () => {
  const defaultSegment = {
    hasFrame: false,
    hasTranscript: false,
    hasAnnotation: false,
    data: [],
  }

  it('renders with minimal height when no data', () => {
    const { container } = render(
      <TimelineSegment
        segment={defaultSegment}
        color="bg-gray-200"
        isHovered={false}
      />
    )
    
    const segment = container.querySelector('[style*="height"]')
    expect(segment?.getAttribute('style')).toContain('20%')
  })

  it('renders with increased height based on data count', () => {
    const segmentWithData = {
      ...defaultSegment,
      data: new Array(7).fill({}),
    }

    const { container } = render(
      <TimelineSegment
        segment={segmentWithData}
        color="bg-blue-500"
        isHovered={false}
      />
    )
    
    const segment = container.querySelector('[style*="height"]')
    expect(segment?.getAttribute('style')).toContain('60%')
  })

  it('renders with full height for many data items', () => {
    const segmentWithManyItems = {
      ...defaultSegment,
      data: new Array(25).fill({}),
    }

    const { container } = render(
      <TimelineSegment
        segment={segmentWithManyItems}
        color="bg-purple-500"
        isHovered={false}
      />
    )
    
    const segment = container.querySelector('[style*="height"]')
    expect(segment?.getAttribute('style')).toContain('100%')
  })

  it('applies hover effect when hovered', () => {
    const { container } = render(
      <TimelineSegment
        segment={defaultSegment}
        color="bg-green-500"
        isHovered={true}
      />
    )
    
    const segment = container.querySelector('.opacity-100')
    expect(segment).toBeInTheDocument()
    
    const segmentWithShadow = container.querySelector('[style*="box-shadow"]')
    expect(segmentWithShadow?.getAttribute('style')).toContain('0 0 10px')
  })

  it('applies correct color class', () => {
    const { container } = render(
      <TimelineSegment
        segment={defaultSegment}
        color="bg-orange-500"
        isHovered={false}
      />
    )
    
    const segment = container.querySelector('.bg-orange-500')
    expect(segment).toBeInTheDocument()
  })
})