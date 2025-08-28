import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import VideoUpload from './VideoUpload'

// Mock fetch
global.fetch = vi.fn()

describe('VideoUpload', () => {
  const mockOnUploadSuccess = vi.fn()
  const mockOnUploadError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload area initially', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    expect(screen.getByText('Click to upload or drag and drop')).toBeInTheDocument()
    expect(screen.getByText('.mkv files only (YYYY-MM-DD_HH-MM-SS.mkv)')).toBeInTheDocument()
  })

  it('rejects non-mkv files', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    const file = new File(['video'], 'test.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })
    
    fireEvent.change(input)
    
    expect(screen.getByText('Only .mkv files are accepted')).toBeInTheDocument()
  })

  it('validates filename format', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    const file = new File(['video'], 'invalid-name.mkv', { type: 'video/x-matroska' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })
    
    fireEvent.change(input)
    
    expect(screen.getByText('Invalid filename format. Expected: YYYY-MM-DD_HH-MM-SS.mkv')).toBeInTheDocument()
  })

  it('accepts valid mkv files', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    const file = new File(['video'], '2024-01-15_14-30-00.mkv', { type: 'video/x-matroska' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })
    
    fireEvent.change(input)
    
    expect(screen.getByText('2024-01-15_14-30-00.mkv')).toBeInTheDocument()
    expect(screen.getByText('Upload Video')).toBeInTheDocument()
  })

  it('rejects files over 5GB', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    const largeFile = new File(['video'], '2024-01-15_14-30-00.mkv', { type: 'video/x-matroska' })
    Object.defineProperty(largeFile, 'size', { value: 6 * 1024 * 1024 * 1024 })
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    Object.defineProperty(input, 'files', {
      value: [largeFile],
      writable: false,
    })
    
    fireEvent.change(input)
    
    expect(screen.getByText('File size must be less than 5GB')).toBeInTheDocument()
  })

  it('uploads file successfully', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: 'test-job-123' }),
    })

    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    const file = new File(['video'], '2024-01-15_14-30-00.mkv', { type: 'video/x-matroska' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })
    
    fireEvent.change(input)
    
    const uploadButton = screen.getByText('Upload Video')
    fireEvent.click(uploadButton)
    
    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalledWith('test-job-123')
    })
  })

  it('handles upload error', async () => {
    const mockFetch = global.fetch as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Upload failed' }),
    })

    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    const file = new File(['video'], '2024-01-15_14-30-00.mkv', { type: 'video/x-matroska' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })
    
    fireEvent.change(input)
    
    const uploadButton = screen.getByText('Upload Video')
    fireEvent.click(uploadButton)
    
    await waitFor(() => {
      expect(mockOnUploadError).toHaveBeenCalledWith('Upload failed')
      expect(screen.getByText('Upload failed')).toBeInTheDocument()
    })
  })

  it('allows canceling selected file', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )
    
    const file = new File(['video'], '2024-01-15_14-30-00.mkv', { type: 'video/x-matroska' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })
    
    fireEvent.change(input)
    
    expect(screen.getByText('2024-01-15_14-30-00.mkv')).toBeInTheDocument()
    
    const cancelButton = screen.getByRole('button', { name: '' })
    fireEvent.click(cancelButton)
    
    expect(screen.queryByText('2024-01-15_14-30-00.mkv')).not.toBeInTheDocument()
    expect(screen.getByText('Click to upload or drag and drop')).toBeInTheDocument()
  })
})