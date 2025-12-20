import React from 'react'

interface SettingToggleProps {
  label: string
  value: boolean
  description?: string
  onChange: (value: boolean) => void
}

export const SettingToggle: React.FC<SettingToggleProps> = ({
  label,
  value,
  description,
  onChange,
}) => {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex-1 pr-4">
        <label className="text-sm font-medium text-forest-700">{label}</label>
        {description && (
          <p className="text-xs text-sage-500 mt-0.5">{description}</p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full
          border-2 border-transparent transition-colors duration-200 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-forest-500 focus:ring-offset-2
          ${value ? 'bg-forest-500' : 'bg-cream-300'}
        `}
      >
        <span
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full
            bg-white shadow ring-0 transition duration-200 ease-in-out
            ${value ? 'translate-x-5' : 'translate-x-0'}
          `}
        />
      </button>
    </div>
  )
}
