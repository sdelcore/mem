import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import PreviewTooltip from './PreviewTooltip'

describe('PreviewTooltip', () => {
  const defaultProps = {
    visible: true,
    x: 100,
    y: 50,
    timestamp: new Date('2024-01-15T14:30:45'),
  }

  it('does not render when not visible', () => {
    const { container } = render(
      <PreviewTooltip {...defaultProps} visible={false} />
    )
    
    expect(container.firstChild).toBeNull()
  })

  it('renders timestamp correctly', () => {
    render(<PreviewTooltip {...defaultProps} />)
    
    expect(screen.getByText('14:30:45')).toBeInTheDocument()
  })

  it('shows frame indicator when hasFrame is true', () => {
    render(<PreviewTooltip {...defaultProps} hasFrame={true} />)
    
    expect(screen.getByText('Frame')).toBeInTheDocument()
  })

  it('shows transcript indicator when hasTranscript is true', () => {
    render(<PreviewTooltip {...defaultProps} hasTranscript={true} />)
    
    expect(screen.getByText('Transcript')).toBeInTheDocument()
  })

  it('shows annotation indicator when hasAnnotation is true', () => {
    render(<PreviewTooltip {...defaultProps} hasAnnotation={true} />)
    
    expect(screen.getByText('Annotation')).toBeInTheDocument()
  })

  it('shows no content message when no content types are present', () => {
    render(<PreviewTooltip {...defaultProps} />)
    
    expect(screen.getByText('No content')).toBeInTheDocument()
  })

  it('renders frame preview image when frameUrl is provided', () => {
    render(
      <PreviewTooltip
        {...defaultProps}
        hasFrame={true}
        frameUrl="http://example.com/frame.jpg"
      />
    )
    
    const img = screen.getByAltText('Frame preview')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', 'http://example.com/frame.jpg')
  })

  it('positions tooltip correctly', () => {
    const { container } = render(<PreviewTooltip {...defaultProps} />)
    
    // With boundary checking, the position might be adjusted
    const tooltip = container.querySelector('.absolute')
    expect(tooltip).toBeInTheDocument()
    
    // Check that style contains positioning
    const style = tooltip?.getAttribute('style')
    expect(style).toContain('left:')
    expect(style).toContain('top:')
    expect(style).toContain('transform: translateX(-50%)')
  })

  it('shows multiple content indicators', () => {
    render(
      <PreviewTooltip
        {...defaultProps}
        hasFrame={true}
        hasTranscript={true}
        hasAnnotation={true}
      />
    )
    
    expect(screen.getByText('Frame')).toBeInTheDocument()
    expect(screen.getByText('Transcript')).toBeInTheDocument()
    expect(screen.getByText('Annotation')).toBeInTheDocument()
    expect(screen.queryByText('No content')).not.toBeInTheDocument()
  })
})