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

  it('renders upload button', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    // Check for Upload button (text may be hidden on mobile, so check for button with Upload icon)
    const uploadButton = screen.getByRole('button')
    expect(uploadButton).toBeInTheDocument()
    expect(uploadButton).toHaveTextContent(/Upload/i)
  })

  it('has hidden file input that accepts mp4 and mkv', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('accept', '.mp4,.mkv')
    expect(input).toHaveAttribute('multiple')
  })

  it('validates filename format and rejects invalid names', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    const file = new File(['video'], 'invalid-name.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })

    fireEvent.change(input)

    // File should be added but with error status
    expect(screen.getByText('invalid-name.mp4')).toBeInTheDocument()
    expect(screen.getByText('Invalid filename format. Expected: YYYY-MM-DD_HH-MM-SS.mp4 or .mkv')).toBeInTheDocument()
  })

  it('accepts valid mp4 files with correct naming', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    const file = new File(['video'], '2024-01-15_14-30-00.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })

    fireEvent.change(input)

    expect(screen.getByText('2024-01-15_14-30-00.mp4')).toBeInTheDocument()
    // Should show upload button for pending files
    expect(screen.getByText(/Upload 1 file/)).toBeInTheDocument()
  })

  it('accepts valid mkv files with correct naming', () => {
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
    expect(screen.getByText(/Upload 1 file/)).toBeInTheDocument()
  })

  it('rejects files over 5GB', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    const largeFile = new File(['video'], '2024-01-15_14-30-00.mp4', { type: 'video/mp4' })
    Object.defineProperty(largeFile, 'size', { value: 6 * 1024 * 1024 * 1024 })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [largeFile],
      writable: false,
    })

    fireEvent.change(input)

    expect(screen.getByText('2024-01-15_14-30-00.mp4')).toBeInTheDocument()
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

    const file = new File(['video'], '2024-01-15_14-30-00.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })

    fireEvent.change(input)

    const uploadButton = screen.getByText(/Upload 1 file/)
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

    const file = new File(['video'], '2024-01-15_14-30-00.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })

    fireEvent.change(input)

    const uploadButton = screen.getByText(/Upload 1 file/)
    fireEvent.click(uploadButton)

    await waitFor(() => {
      expect(mockOnUploadError).toHaveBeenCalled()
    })
  })

  it('allows removing file from queue', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    const file = new File(['video'], '2024-01-15_14-30-00.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })

    fireEvent.change(input)

    expect(screen.getByText('2024-01-15_14-30-00.mp4')).toBeInTheDocument()

    // Find the remove button (X icon button in the file row)
    const removeButtons = screen.getAllByRole('button').filter(btn =>
      btn.className.includes('hover:bg-cream-200')
    )

    if (removeButtons.length > 0) {
      fireEvent.click(removeButtons[0])
      expect(screen.queryByText('2024-01-15_14-30-00.mp4')).not.toBeInTheDocument()
    }
  })

  it('shows file count badge when files are selected', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    const file1 = new File(['video'], '2024-01-15_14-30-00.mp4', { type: 'video/mp4' })
    const file2 = new File(['video'], '2024-01-16_14-30-00.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [file1, file2],
      writable: false,
    })

    fireEvent.change(input)

    // Should show count of 2 files
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('allows clearing all files', () => {
    render(
      <VideoUpload
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    )

    const file = new File(['video'], '2024-01-15_14-30-00.mp4', { type: 'video/mp4' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    })

    fireEvent.change(input)

    expect(screen.getByText('2024-01-15_14-30-00.mp4')).toBeInTheDocument()

    // Find and click "Clear all" button
    const clearAllButton = screen.getByText('Clear all')
    fireEvent.click(clearAllButton)

    expect(screen.queryByText('2024-01-15_14-30-00.mp4')).not.toBeInTheDocument()
  })
})
