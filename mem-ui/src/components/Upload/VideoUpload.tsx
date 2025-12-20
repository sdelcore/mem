import React, { useState, useRef } from 'react'
import { Upload, X, CheckCircle, AlertCircle, FileVideo, Clock } from 'lucide-react'
import { API_BASE_URL } from '../../utils/config'

interface VideoUploadProps {
  onUploadSuccess: (jobId: string) => void
  onUploadError: (error: string) => void
}

interface FileStatus {
  file: File
  status: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
  jobId?: string
  progress?: number
}

const VideoUpload: React.FC<VideoUploadProps> = ({
  onUploadSuccess,
  onUploadError,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<FileStatus[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [currentUploadIndex, setCurrentUploadIndex] = useState(-1)
  const [showFileList, setShowFileList] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFileName = (fileName: string): boolean => {
    // Expected format: YYYY-MM-DD_HH-MM-SS.(mp4|mkv)
    const pattern = /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.(mp4|mkv)$/
    return pattern.test(fileName)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const newFileStatuses: FileStatus[] = []

    files.forEach(file => {
      // Validate filename format (includes extension check)
      if (!validateFileName(file.name)) {
        newFileStatuses.push({
          file,
          status: 'error',
          error: 'Invalid filename format. Expected: YYYY-MM-DD_HH-MM-SS.mp4 or .mkv'
        })
        return
      }

      // Check file size (max 5GB)
      const maxSize = 5 * 1024 * 1024 * 1024
      if (file.size > maxSize) {
        newFileStatuses.push({
          file,
          status: 'error',
          error: 'File size must be less than 5GB'
        })
        return
      }

      // Valid file
      newFileStatuses.push({
        file,
        status: 'pending'
      })
    })

    setSelectedFiles(prev => [...prev, ...newFileStatuses])
    setShowFileList(true)
    
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const uploadFile = async (fileStatus: FileStatus): Promise<void> => {
    const formData = new FormData()
    formData.append('file', fileStatus.file)

    try {
      const response = await fetch(`${API_BASE_URL}/api/capture`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const result = await response.json()
      
      // Update file status to success
      setSelectedFiles(prev => prev.map(fs => 
        fs.file === fileStatus.file 
          ? { ...fs, status: 'success', jobId: result.job_id }
          : fs
      ))
      
      onUploadSuccess(result.job_id)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      
      // Update file status to error
      setSelectedFiles(prev => prev.map(fs => 
        fs.file === fileStatus.file 
          ? { ...fs, status: 'error', error: errorMessage }
          : fs
      ))
      
      onUploadError(`${fileStatus.file.name}: ${errorMessage}`)
    }
  }

  const startUpload = async () => {
    const pendingFiles = selectedFiles.filter(fs => fs.status === 'pending')
    if (!pendingFiles.length) return

    setIsUploading(true)

    // Upload files sequentially
    for (let i = 0; i < pendingFiles.length; i++) {
      setCurrentUploadIndex(i)
      
      // Update status to uploading
      setSelectedFiles(prev => prev.map(fs => 
        fs.file === pendingFiles[i].file 
          ? { ...fs, status: 'uploading' }
          : fs
      ))
      
      await uploadFile(pendingFiles[i])
    }

    setIsUploading(false)
    setCurrentUploadIndex(-1)
  }

  const removeFile = (file: File) => {
    setSelectedFiles(prev => prev.filter(fs => fs.file !== file))
  }

  const clearCompleted = () => {
    setSelectedFiles(prev => prev.filter(fs => fs.status === 'pending' || fs.status === 'uploading'))
  }

  const clearAll = () => {
    if (isUploading) return
    setSelectedFiles([])
    setShowFileList(false)
  }

  const getStatusIcon = (status: FileStatus['status']) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4 text-sage-400" />
      case 'uploading':
        return (
          <div className="relative">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-cream-200"></div>
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-transparent border-t-sage-300 absolute top-0"></div>
          </div>
        )
      case 'success':
        return <CheckCircle className="w-4 h-4 text-sage-500" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />
    }
  }

  const pendingCount = selectedFiles.filter(fs => fs.status === 'pending').length
  const successCount = selectedFiles.filter(fs => fs.status === 'success').length
  const errorCount = selectedFiles.filter(fs => fs.status === 'error').length
  const totalCount = selectedFiles.length

  return (
    <div className="relative">
      {/* Upload button */}
      <div className="flex items-center gap-2">
        <button
          className="flex items-center gap-2 px-4 py-2.5 min-h-11 bg-forest-500 text-cream-50 rounded-lg font-medium text-sm hover:bg-forest-600 transition-colors duration-150"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-5 h-5" />
          <span className="hidden sm:inline">Upload</span>
          {totalCount > 0 && (
            <span className="ml-1 px-2 py-0.5 bg-forest-600 rounded-full text-xs">
              {totalCount}
            </span>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.mkv"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
        </button>

        {totalCount > 0 && (
          <button
            onClick={() => setShowFileList(!showFileList)}
            className="p-2.5 min-h-11 min-w-11 bg-cream-100 rounded-lg hover:bg-cream-200 transition-colors flex items-center justify-center"
          >
            <FileVideo className="w-5 h-5 text-forest-600" />
          </button>
        )}
      </div>

      {/* File list - responsive width */}
      {showFileList && selectedFiles.length > 0 && (
        <div className="fixed inset-x-4 top-20 sm:absolute sm:inset-x-auto sm:top-full sm:mt-2 sm:right-0 sm:w-96 max-w-[400px] max-h-[70vh] sm:max-h-96 overflow-y-auto bg-white rounded-lg border border-cream-200 shadow-flat z-50">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-cream-200 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-medium text-forest-700">Upload Queue</h3>
              <div className="flex items-center gap-2 text-xs text-sage-500">
                {pendingCount > 0 && <span>{pendingCount} pending</span>}
                {successCount > 0 && <span className="text-sage-500">{successCount} completed</span>}
                {errorCount > 0 && <span className="text-red-600">{errorCount} failed</span>}
              </div>
            </div>
            <button
              onClick={() => setShowFileList(false)}
              className="p-2 min-h-11 min-w-11 hover:bg-cream-100 rounded-lg transition-colors flex items-center justify-center"
            >
              <X className="w-5 h-5 text-sage-400" />
            </button>
          </div>

          {/* File items */}
          <div className="divide-y divide-cream-200">
            {selectedFiles.map((fileStatus, index) => (
              <div key={index} className="px-4 py-3 hover:bg-cream-50">
                <div className="flex items-start gap-3">
                  {getStatusIcon(fileStatus.status)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-forest-700 truncate">
                      {fileStatus.file.name}
                    </p>
                    <p className="text-xs text-sage-400">
                      {(fileStatus.file.size / (1024 * 1024)).toFixed(1)} MB
                    </p>
                    {fileStatus.error && (
                      <p className="text-xs text-red-600 mt-1">{fileStatus.error}</p>
                    )}
                    {fileStatus.jobId && (
                      <p className="text-xs text-sage-500 mt-1">Job ID: {fileStatus.jobId}</p>
                    )}
                  </div>
                  {fileStatus.status === 'pending' && !isUploading && (
                    <button
                      onClick={() => removeFile(fileStatus.file)}
                      className="p-2 min-h-10 min-w-10 hover:bg-cream-200 rounded-lg transition-colors flex items-center justify-center"
                    >
                      <X className="w-4 h-4 text-sage-400" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Actions - stack on mobile */}
          <div className="sticky bottom-0 bg-white border-t border-cream-200 px-4 py-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              {!isUploading && pendingCount > 0 && (
                <button
                  onClick={startUpload}
                  className="w-full sm:w-auto px-4 py-2.5 min-h-11 bg-sage-300 text-white text-sm font-medium rounded-lg hover:bg-sage-400 transition-colors duration-150"
                >
                  Upload {pendingCount} file{pendingCount !== 1 ? 's' : ''}
                </button>
              )}
              {isUploading && (
                <span className="text-sm text-sage-500 text-center sm:text-left">
                  Uploading {currentUploadIndex + 1} of {pendingCount}...
                </span>
              )}
              <div className="flex items-center justify-center sm:justify-end gap-4">
                {successCount > 0 && (
                  <button
                    onClick={clearCompleted}
                    className="py-2 px-3 min-h-11 text-sm text-sage-500 hover:text-sage-600"
                  >
                    Clear completed
                  </button>
                )}
                {!isUploading && (
                  <button
                    onClick={clearAll}
                    className="py-2 px-3 min-h-11 text-sm text-red-500 hover:text-red-600"
                  >
                    Clear all
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default VideoUpload