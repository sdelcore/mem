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
    <>
      {/* Mobile backdrop */}
      {!isCollapsed && (
        <div
          className="fixed inset-0 bg-black/50 md:hidden z-40"
          onClick={onToggleCollapse}
          aria-hidden="true"
        />
      )}

      <div className={`
        ${/* Mobile: full-screen overlay when open, hidden when collapsed */''}
        fixed inset-y-0 right-0 z-50 md:relative md:z-auto
        ${isCollapsed
          ? 'w-0 md:w-12 invisible md:visible'
          : 'w-full sm:w-80 md:w-64 visible'
        }
        bg-forest-600 h-screen flex border-l md:border-r border-cream-200 transition-all duration-300 ease-in-out
      `}>
        {/* Collapse Toggle Button */}
        <button
          onClick={onToggleCollapse}
          className={`
            absolute top-4 -left-12 md:left-0 md:top-1/2
            md:-translate-y-1/2 md:-translate-x-1/2
            min-h-11 min-w-11 p-2.5
            bg-forest-500 hover:bg-forest-400 text-cream-100
            rounded-full shadow-flat transition-colors duration-150 z-50
            flex items-center justify-center
            ${isCollapsed ? 'hidden md:flex' : 'flex'}
          `}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <ChevronLeft className="w-5 h-5" />
          ) : (
            <ChevronRight className="w-5 h-5" />
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
          <div className="hidden md:flex items-center justify-center h-full w-full">
            <p className="text-cream-200 text-xs font-medium transform -rotate-90 whitespace-nowrap">
              Timeline
            </p>
          </div>
        )}
      </div>
    </>
  )
}

export default Sidebar