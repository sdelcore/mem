import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import DateSelector from './DateSelector'
import VerticalActivityTimeline from './VerticalActivityTimeline'

interface SidebarProps {
  selectedDate: Date
  onDateChange: (date: Date) => void
  onTimeSelect: (time: Date) => void
  onRangeSelect?: (start: Date, end: Date) => void
  data?: any[]
  currentTime?: Date
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

const Sidebar: React.FC<SidebarProps> = ({
  selectedDate,
  onDateChange,
  onTimeSelect,
  onRangeSelect,
  data = [],
  currentTime = new Date(),
  isCollapsed = false,
  onToggleCollapse,
}) => {
  return (
    <div className={`relative bg-forest-600 h-screen flex border-r border-cream-200 transition-all duration-300 ease-in-out ${
      isCollapsed ? 'w-12' : 'w-64'
    }`}>
      {/* Collapse Toggle Button */}
      <button
        onClick={onToggleCollapse}
        className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 bg-forest-500 hover:bg-forest-400 text-cream-100 p-1.5 rounded-full shadow-flat transition-colors duration-150 z-50"
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? (
          <ChevronLeft className="w-4 h-4" />
        ) : (
          <ChevronRight className="w-4 h-4" />
        )}
      </button>

      {/* Sidebar Content */}
      <div className={`flex flex-col w-full transition-opacity duration-300 ${
        isCollapsed ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}>
        {/* Date Selector */}
        <div className="p-3 border-b border-forest-500 flex-shrink-0">
          <DateSelector
            selectedDate={selectedDate}
            onDateChange={onDateChange}
          />
        </div>

        {/* Vertical Timeline - Scrollable */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          <VerticalActivityTimeline
            selectedDate={selectedDate}
            onTimeSelect={onTimeSelect}
            onRangeSelect={onRangeSelect}
            data={data}
            currentTime={currentTime}
          />
        </div>

        {/* Footer Info */}
        <div className="p-2 border-t border-forest-500 text-center flex-shrink-0">
          <p className="text-xs text-sage-300">
            Click to navigate • Drag to select
          </p>
        </div>
      </div>

      {/* Collapsed State - Show vertical text */}
      {isCollapsed && (
        <div className="flex items-center justify-center h-full w-full">
          <p className="text-cream-200 text-xs font-medium transform -rotate-90 whitespace-nowrap">
            Timeline
          </p>
        </div>
      )}
    </div>
  )
}

export default Sidebar