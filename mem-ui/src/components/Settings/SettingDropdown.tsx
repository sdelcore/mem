import React from 'react'
import { ChevronDown } from 'lucide-react'

interface SettingDropdownProps {
  label: string
  value: string
  options: { value: string; label: string }[]
  description?: string
  onChange: (value: string) => void
}

export const SettingDropdown: React.FC<SettingDropdownProps> = ({
  label,
  value,
  options,
  description,
  onChange,
}) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-forest-700">{label}</label>
      </div>
      {description && (
        <p className="text-xs text-sage-500">{description}</p>
      )}
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="
            w-full appearance-none bg-cream-50 border border-cream-200 rounded-lg
            px-4 py-2.5 pr-10 text-sm text-forest-700
            focus:outline-none focus:ring-2 focus:ring-forest-500 focus:border-transparent
            cursor-pointer
          "
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sage-400 pointer-events-none" />
      </div>
    </div>
  )
}
