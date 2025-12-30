import { useState, useMemo, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import DatePicker from 'react-datepicker'
import { Menu, X, Settings, Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import TimelineComponent from '../components/Timeline/Timeline'
import VideoUpload from '../components/Upload/VideoUpload'
import SearchBar from '../components/Search/SearchBar'
import ContentViewer from '../components/Content/ContentViewer'
import StreamManager from '../components/Stream/StreamManager'
import { VoiceProfileManager } from '../components/VoiceProfile'
import VoiceRecorder from '../components/VoiceRecorder/VoiceRecorder'
import { useTimeline } from '../hooks/useTimeline'
import 'react-datepicker/dist/react-datepicker.css'

function Timeline() {
  const [selectedTime, setSelectedTime] = useState<Date | null>(null)
  const [selectedRange, setSelectedRange] = useState<{ start: Date; end: Date } | null>(null)
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [timeOffset, setTimeOffset] = useState(0)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [showCalendar, setShowCalendar] = useState(false)
  const calendarRef = useRef<HTMLDivElement>(null)

  // Close calendar when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (calendarRef.current && !calendarRef.current.contains(event.target as Node)) {
        setShowCalendar(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Calculate time range based on selected date and offset (always 24h view)
  const { startTime, endTime } = useMemo(() => {
    const start = new Date(selectedDate)
    const end = new Date(selectedDate)

    // Show full day with day offset
    start.setHours(0, 0, 0, 0)
    start.setDate(start.getDate() + timeOffset)
    end.setHours(23, 59, 59, 999)
    end.setDate(end.getDate() + timeOffset)

    return { startTime: start, endTime: end }
  }, [selectedDate, timeOffset])

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

  const handleNavigateToUpload = (timestamp: Date) => {
    setSelectedDate(timestamp)
    setSelectedTime(timestamp)
    setTimeOffset(0)
    setIsMobileMenuOpen(false)
  }

  const handleDateChange = (date: Date) => {
    setSelectedDate(date)
    // Clear selections and reset offset when changing date
    setSelectedTime(null)
    setSelectedRange(null)
    setTimeOffset(0)
    setShowCalendar(false)
  }

  const handlePreviousDay = () => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() - 1)
    handleDateChange(newDate)
  }

  const handleNextDay = () => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() + 1)
    // Don't allow future dates
    if (newDate <= new Date()) {
      handleDateChange(newDate)
    }
  }

  const isToday = format(selectedDate, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')

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
            <div className="flex items-center justify-between h-14 sm:h-16">
              {/* Logo */}
              <div className="flex items-center space-x-2 sm:space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-forest-500 flex items-center justify-center">
                  <span className="text-cream-50 font-bold text-base sm:text-lg">M</span>
                </div>
                <div>
                  <h1 className="text-lg sm:text-xl font-bold text-forest-600">
                    Mem Timeline
                  </h1>
                  <p className="hidden sm:block text-xs text-sage-400">Visual Memory Explorer</p>
                </div>
              </div>

              {/* Mobile hamburger menu button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden p-2.5 min-h-11 min-w-11 flex items-center justify-center rounded-lg hover:bg-forest-100 transition-colors"
                aria-label="Toggle menu"
              >
                {isMobileMenuOpen ? (
                  <X className="w-6 h-6 text-forest-600" />
                ) : (
                  <Menu className="w-6 h-6 text-forest-600" />
                )}
              </button>

              {/* Desktop controls */}
              <div className="hidden md:flex items-center gap-4">
                {/* Calendar Date Picker */}
                <div className="relative" ref={calendarRef}>
                  <div className="flex items-center bg-cream-50 rounded-lg border border-cream-200">
                    <button
                      onClick={handlePreviousDay}
                      className="p-2.5 hover:bg-cream-100 rounded-l-lg transition-colors"
                      aria-label="Previous day"
                    >
                      <ChevronLeft className="w-5 h-5 text-forest-600" />
                    </button>
                    <button
                      onClick={() => setShowCalendar(!showCalendar)}
                      className="flex items-center gap-2 px-4 py-2 min-h-11 text-sm font-medium text-forest-600 hover:bg-cream-100 transition-colors"
                    >
                      <Calendar className="w-4 h-4" />
                      <span className="min-w-[4.5rem]">{format(selectedDate, 'MMM dd')}</span>
                    </button>
                    <button
                      onClick={handleNextDay}
                      disabled={isToday}
                      className="p-2.5 hover:bg-cream-100 rounded-r-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Next day"
                    >
                      <ChevronRight className="w-5 h-5 text-forest-600" />
                    </button>
                  </div>
                  {showCalendar && (
                    <div className="absolute top-full mt-2 right-0 z-50 bg-white rounded-lg shadow-lg border border-cream-200 p-2">
                      <DatePicker
                        selected={selectedDate}
                        onChange={(date) => date && handleDateChange(date)}
                        maxDate={new Date()}
                        inline
                        calendarClassName="earthy-calendar"
                      />
                      {!isToday && (
                        <button
                          onClick={() => {
                            setSelectedDate(new Date())
                            setTimeOffset(0)
                            setShowCalendar(false)
                          }}
                          className="w-full mt-2 px-3 py-2 bg-forest-500 hover:bg-forest-600 text-white text-sm rounded-lg transition-colors"
                        >
                          Go to Today
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <SearchBar
                  placeholder="Search transcripts..."
                  onSearch={() => {}}
                  onResultClick={handleSearchResultClick}
                />
                <VoiceProfileManager />
                <VoiceRecorder />
                <StreamManager />
                <VideoUpload
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={(error) => console.error('Upload error:', error)}
                  onNavigateToTime={handleNavigateToUpload}
                />
                {/* Settings Link */}
                <Link
                  to="/settings"
                  className="p-2.5 min-h-11 min-w-11 flex items-center justify-center rounded-lg hover:bg-forest-100 transition-colors"
                  title="Settings"
                >
                  <Settings className="w-5 h-5 text-forest-600" />
                </Link>
              </div>
            </div>
          </div>

          {/* Mobile menu dropdown */}
          {isMobileMenuOpen && (
            <div className="md:hidden absolute top-14 left-0 right-0 bg-cream-100/95 backdrop-blur-lg border-b border-sage-200/50 shadow-lg z-50 animate-slide-down">
              <div className="px-4 py-4 space-y-4">
                {/* Date picker for mobile */}
                <div className="bg-cream-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-3">
                    <button
                      onClick={handlePreviousDay}
                      className="p-2 min-h-11 min-w-11 hover:bg-cream-200 rounded-lg transition-colors flex items-center justify-center"
                      aria-label="Previous day"
                    >
                      <ChevronLeft className="w-5 h-5 text-forest-600" />
                    </button>
                    <div className="flex flex-col items-center">
                      <span className="text-lg font-semibold text-forest-700">
                        {format(selectedDate, 'EEEE')}
                      </span>
                      <span className="text-sm text-sage-500">
                        {format(selectedDate, 'MMM dd, yyyy')}
                      </span>
                    </div>
                    <button
                      onClick={handleNextDay}
                      disabled={isToday}
                      className="p-2 min-h-11 min-w-11 hover:bg-cream-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                      aria-label="Next day"
                    >
                      <ChevronRight className="w-5 h-5 text-forest-600" />
                    </button>
                  </div>
                  <div className="flex justify-center">
                    <DatePicker
                      selected={selectedDate}
                      onChange={(date) => {
                        if (date) {
                          handleDateChange(date)
                          setIsMobileMenuOpen(false)
                        }
                      }}
                      maxDate={new Date()}
                      inline
                      calendarClassName="earthy-calendar"
                    />
                  </div>
                  {!isToday && (
                    <button
                      onClick={() => {
                        setSelectedDate(new Date())
                        setTimeOffset(0)
                        setIsMobileMenuOpen(false)
                      }}
                      className="w-full mt-3 px-4 py-2.5 min-h-11 bg-forest-500 hover:bg-forest-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      Go to Today
                    </button>
                  )}
                </div>

                {/* Search - full width */}
                <SearchBar
                  placeholder="Search transcripts..."
                  onSearch={() => {}}
                  onResultClick={(timestamp) => {
                    handleSearchResultClick(timestamp)
                    setIsMobileMenuOpen(false)
                  }}
                />

                {/* Action buttons row */}
                <div className="flex gap-3">
                  <VoiceProfileManager />
                  <VoiceRecorder />
                  <StreamManager />
                  <VideoUpload
                    onUploadSuccess={handleUploadSuccess}
                    onUploadError={(error) => console.error('Upload error:', error)}
                    onNavigateToTime={handleNavigateToUpload}
                  />
                  <Link
                    to="/settings"
                    className="p-2.5 min-h-11 min-w-11 flex items-center justify-center bg-sage-300 text-cream-50 rounded-lg hover:bg-sage-400 transition-colors"
                    title="Settings"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <Settings className="w-5 h-5" />
                  </Link>
                </div>
              </div>
            </div>
          )}
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
            <div className="space-y-3">
              {/* Skeleton time labels */}
              <div className="flex justify-between">
                <div className="h-4 w-32 bg-cream-200 rounded animate-pulse"></div>
                <div className="h-4 w-24 bg-cream-200 rounded animate-pulse"></div>
                <div className="h-4 w-32 bg-cream-200 rounded animate-pulse"></div>
              </div>
              {/* Skeleton hint */}
              <div className="h-3 w-48 bg-cream-200 rounded animate-pulse"></div>
              {/* Skeleton timeline bars */}
              <div className="timeline-skeleton flex items-end gap-0.5 h-32 bg-cream-50 rounded-lg p-2 border border-cream-200">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-cream-200 rounded-sm animate-pulse"
                    style={{ height: `${Math.random() * 60 + 20}%`, animationDelay: `${i * 50}ms` }}
                  ></div>
                ))}
              </div>
              <p className="text-sm text-sage-400 text-center animate-pulse">Loading timeline data...</p>
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
            <TimelineComponent
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

        {/* Content Viewer - always show, defaults to full range */}
        <div className="bg-white rounded-lg shadow-flat p-6 border border-cream-200">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-8 rounded-full bg-sage-300"></div>
              <h2 className="text-xl font-semibold text-forest-700">
                {selectedRange ? 'Selected Range' : selectedTime ? 'Selected Time' : 'Timeline Content'}
              </h2>
              <span className="text-sm text-sage-400 ml-2">
                {selectedTime && format(selectedTime, 'HH:mm:ss')}
                {selectedRange && `${format(selectedRange.start, 'HH:mm:ss')} - ${format(selectedRange.end, 'HH:mm:ss')}`}
                {!selectedTime && !selectedRange && `${format(startTime, 'HH:mm')} - ${format(endTime, 'HH:mm')}`}
              </span>
            </div>
            {(selectedTime || selectedRange) && (
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
            )}
          </div>
          <ContentViewer
            startTime={selectedRange?.start || selectedTime || startTime}
            endTime={selectedRange?.end || (selectedTime ? undefined : endTime)}
            data={timelineData}
          />
        </div>
      </main>
    </div>
  </div>
  )
}

export default Timeline
