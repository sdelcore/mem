import { useState, useMemo } from 'react'
import { format } from 'date-fns'
import Timeline from './components/Timeline/Timeline'
import VideoUpload from './components/Upload/VideoUpload'
import SearchBar from './components/Search/SearchBar'
import ContentViewer from './components/Content/ContentViewer'
import Sidebar from './components/Sidebar/Sidebar'
import { useTimeline } from './hooks/useTimeline'

function App() {
  const [selectedTime, setSelectedTime] = useState<Date | null>(null)
  const [selectedRange, setSelectedRange] = useState<{ start: Date; end: Date } | null>(null)
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [viewMode, setViewMode] = useState<'24h' | '12h' | '6h'>('12h')
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true)
  const [timeOffset, setTimeOffset] = useState(0)

  // Calculate time range based on selected date, view mode, and offset
  const { startTime, endTime } = useMemo(() => {
    const start = new Date(selectedDate)
    const end = new Date(selectedDate)
    
    if (viewMode === '24h') {
      // Show full day with day offset
      start.setHours(0, 0, 0, 0)
      start.setDate(start.getDate() + timeOffset)
      end.setHours(23, 59, 59, 999)
      end.setDate(end.getDate() + timeOffset)
    } else if (viewMode === '12h') {
      // Show 12-hour periods (AM/PM)
      // timeOffset 0 = 00:00-11:59 (AM)
      // timeOffset 1 = 12:00-23:59 (PM)
      // timeOffset -1 = previous day PM
      // timeOffset 2 = next day AM
      const dayOffset = Math.floor(timeOffset / 2)
      const isPM = timeOffset % 2 !== 0
      
      start.setDate(start.getDate() + dayOffset)
      start.setHours(isPM ? 12 : 0, 0, 0, 0)
      
      end.setDate(end.getDate() + dayOffset)
      end.setHours(isPM ? 23 : 11, 59, 59, 999)
    } else if (viewMode === '6h') {
      // Show 6-hour quarters of the day
      // timeOffset 0 = 00:00-05:59
      // timeOffset 1 = 06:00-11:59
      // timeOffset 2 = 12:00-17:59
      // timeOffset 3 = 18:00-23:59
      const dayOffset = Math.floor(timeOffset / 4)
      const quarter = timeOffset % 4
      const startHour = quarter * 6
      
      start.setDate(start.getDate() + dayOffset)
      start.setHours(startHour, 0, 0, 0)
      
      end.setDate(end.getDate() + dayOffset)
      end.setHours(startHour + 5, 59, 59, 999)
    }
    
    return { startTime: start, endTime: end }
  }, [selectedDate, viewMode, timeOffset])

  const { data: timelineData, isLoading, error, refetch } = useTimeline(startTime, endTime)

  const handleTimeSelect = (time: Date) => {
    setSelectedTime(time)
    setSelectedRange(null)
  }

  const handleRangeSelect = (start: Date, end: Date) => {
    setSelectedRange({ start, end })
    setSelectedTime(null)
  }

  const handleUploadSuccess = (jobId: string) => {
    console.log('Upload successful, job ID:', jobId)
    // Poll for job completion and refresh timeline
    setTimeout(() => refetch(), 5000)
  }

  const handleSearchResultClick = (timestamp: Date) => {
    setSelectedTime(timestamp)
    setSelectedRange(null)
  }

  const handleDateChange = (date: Date) => {
    setSelectedDate(date)
    // Clear selections and reset offset when changing date
    setSelectedTime(null)
    setSelectedRange(null)
    setTimeOffset(0)
  }

  const handleViewModeChange = (mode: '24h' | '12h' | '6h') => {
    setViewMode(mode)
    // Reset offset when changing view mode
    setTimeOffset(0)
  }

  const handleNavigatePrevious = () => {
    setTimeOffset(prev => prev - 1)
  }

  const handleNavigateNext = () => {
    setTimeOffset(prev => prev + 1)
  }

  return (
    <div className="h-screen bg-cream-50 flex overflow-hidden">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="sticky top-0 z-40 bg-cream-100/90 backdrop-blur-lg border-b border-sage-200/50 shadow-sm">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-lg bg-forest-500 flex items-center justify-center">
                  <span className="text-cream-50 font-bold text-lg">M</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-forest-600">
                    Mem Timeline
                  </h1>
                  <p className="text-xs text-sage-400">Visual Memory Explorer</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {/* View Mode Toggle */}
                <div className="flex items-center gap-1 bg-forest-100 rounded-lg p-1">
                  <button
                    onClick={() => handleViewModeChange('6h')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      viewMode === '6h' ? 'bg-forest-500 text-cream-50' : 'text-forest-600 hover:bg-forest-200'
                    }`}
                  >
                    6h
                  </button>
                  <button
                    onClick={() => handleViewModeChange('12h')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      viewMode === '12h' ? 'bg-forest-500 text-cream-50' : 'text-forest-600 hover:bg-forest-200'
                    }`}
                  >
                    12h
                  </button>
                  <button
                    onClick={() => handleViewModeChange('24h')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      viewMode === '24h' ? 'bg-forest-500 text-cream-50' : 'text-forest-600 hover:bg-forest-200'
                    }`}
                  >
                    24h
                  </button>
                </div>
                <SearchBar
                  placeholder="Search transcripts..."
                  onSearch={() => {}}
                  onResultClick={handleSearchResultClick}
                />
                <VideoUpload
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={(error) => console.error('Upload error:', error)}
                />
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 px-4 sm:px-6 lg:px-8 py-8 space-y-6 overflow-y-auto">
        {/* Timeline */}
        <div className="bg-white rounded-lg shadow-flat p-6 border border-cream-200">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-8 rounded-full bg-forest-500"></div>
              <h2 className="text-xl font-semibold text-forest-700">Timeline</h2>
              <span className="text-sm text-sage-400 ml-2">
                {format(startTime, 'MMM dd, HH:mm')} - {format(endTime, 'HH:mm')}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm text-sage-400">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-sage-300"></div>
                <span>Live</span>
              </div>
            </div>
          </div>
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-32 space-y-3">
              <div className="relative">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-cream-200"></div>
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-transparent border-t-sage-300 absolute top-0"></div>
              </div>
              <p className="text-sm text-sage-400 animate-pulse">Loading timeline data...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-32 space-y-2">
              <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                <span className="text-red-600 text-xl">!</span>
              </div>
              <p className="text-red-600 font-medium">Failed to load timeline</p>
              <p className="text-sm text-sage-400">{error.message}</p>
            </div>
          ) : (
            <Timeline
              startTime={startTime}
              endTime={endTime}
              data={timelineData}
              onTimeSelect={handleTimeSelect}
              onRangeSelect={handleRangeSelect}
              onNavigatePrevious={handleNavigatePrevious}
              onNavigateNext={handleNavigateNext}
            />
          )}
        </div>

        {/* Content Viewer */}
        {(selectedTime || selectedRange) && (
          <div className="bg-white rounded-lg shadow-flat p-6 animate-fade-in border border-cream-200">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="w-2 h-8 rounded-full bg-sage-300"></div>
                <h2 className="text-xl font-semibold text-forest-700">
                  {selectedRange ? 'Selected Range' : 'Selected Time'}
                </h2>
                <span className="text-sm text-sage-400 ml-2">
                  {selectedTime && format(selectedTime, 'HH:mm:ss')}
                  {selectedRange && `${format(selectedRange.start, 'HH:mm:ss')} - ${format(selectedRange.end, 'HH:mm:ss')}`}
                </span>
              </div>
              <button
                onClick={() => {
                  setSelectedTime(null)
                  setSelectedRange(null)
                }}
                className="text-sage-400 hover:text-forest-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <ContentViewer
              startTime={selectedRange?.start || selectedTime!}
              endTime={selectedRange?.end}
              data={timelineData}
            />
          </div>
        )}
      </main>
    </div>

    {/* Sidebar */}
    <Sidebar
      selectedDate={selectedDate}
      onDateChange={handleDateChange}
      onTimeSelect={handleTimeSelect}
      onRangeSelect={handleRangeSelect}
      data={timelineData || []}
      currentTime={new Date()}
      isCollapsed={isSidebarCollapsed}
      onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
    />
  </div>
  )
}

export default App