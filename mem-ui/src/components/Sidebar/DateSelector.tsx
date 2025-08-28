import React, { useState } from 'react'
import DatePicker from 'react-datepicker'
import { format } from 'date-fns'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import 'react-datepicker/dist/react-datepicker.css'

interface DateSelectorProps {
  selectedDate: Date
  onDateChange: (date: Date) => void
}

const DateSelector: React.FC<DateSelectorProps> = ({
  selectedDate,
  onDateChange,
}) => {
  const [showCalendar, setShowCalendar] = useState(false)
  const handlePreviousDay = () => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() - 1)
    onDateChange(newDate)
  }

  const handleNextDay = () => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() + 1)
    // Don't allow future dates
    if (newDate <= new Date()) {
      onDateChange(newDate)
    }
  }

  const handleToday = () => {
    onDateChange(new Date())
  }

  const handleDateSelect = (date: Date) => {
    onDateChange(date)
    setShowCalendar(false)
  }

  const isToday = format(selectedDate, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')

  return (
    <div className="space-y-3">
      {/* Date Display */}
      <div className="bg-forest-700 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={handlePreviousDay}
            className="p-1 hover:bg-forest-600 rounded transition-colors"
            aria-label="Previous day"
          >
            <ChevronLeft className="w-4 h-4 text-cream-200" />
          </button>
          
          <button
            onClick={() => setShowCalendar(!showCalendar)}
            className="flex flex-col items-center px-2 py-1 hover:bg-forest-600 rounded transition-colors cursor-pointer"
            aria-label="Toggle calendar"
          >
            <div className="flex items-center gap-1">
              <p className="text-cream-100 font-semibold text-lg">
                {format(selectedDate, 'EEEE')}
              </p>
              <Calendar className="w-3 h-3 text-sage-300" />
            </div>
            <p className="text-sage-300 text-sm">
              {format(selectedDate, 'MMM dd, yyyy')}
            </p>
          </button>

          <button
            onClick={handleNextDay}
            disabled={isToday}
            className="p-1 hover:bg-forest-600 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Next day"
          >
            <ChevronRight className="w-4 h-4 text-cream-200" />
          </button>
        </div>

        {/* Today Button */}
        {!isToday && (
          <button
            onClick={handleToday}
            className="w-full mt-2 px-3 py-1.5 bg-sage-400 hover:bg-sage-500 text-white text-sm rounded-lg transition-colors"
          >
            Go to Today
          </button>
        )}
      </div>

      {/* Calendar Picker - Only shown when toggled */}
      {showCalendar && (
        <div className="datepicker-wrapper animate-fade-in">
          <DatePicker
            selected={selectedDate}
            onChange={(date) => date && handleDateSelect(date!)}
            maxDate={new Date()}
            inline
            calendarClassName="earthy-calendar"
          />
        </div>
      )}
    </div>
  )
}

export default DateSelector