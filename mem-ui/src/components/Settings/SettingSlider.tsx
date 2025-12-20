import React from 'react'

interface SettingSliderProps {
  label: string
  value: number
  min: number
  max: number
  step?: number
  unit?: string
  description?: string
  onChange: (value: number) => void
}

export const SettingSlider: React.FC<SettingSliderProps> = ({
  label,
  value,
  min,
  max,
  step = 1,
  unit = '',
  description,
  onChange,
}) => {
  const percentage = ((value - min) / (max - min)) * 100

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-forest-700">{label}</label>
        <span className="text-sm font-mono text-sage-600 bg-cream-100 px-2 py-0.5 rounded">
          {value}
          {unit}
        </span>
      </div>
      {description && (
        <p className="text-xs text-sage-500">{description}</p>
      )}
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-2 bg-cream-200 rounded-lg appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:h-4
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:bg-forest-500
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:shadow-md
            [&::-webkit-slider-thumb]:transition-transform
            [&::-webkit-slider-thumb]:hover:scale-110
            [&::-moz-range-thumb]:w-4
            [&::-moz-range-thumb]:h-4
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:bg-forest-500
            [&::-moz-range-thumb]:cursor-pointer
            [&::-moz-range-thumb]:border-none"
          style={{
            background: `linear-gradient(to right, rgb(var(--color-forest-500)) 0%, rgb(var(--color-forest-500)) ${percentage}%, rgb(var(--color-cream-200)) ${percentage}%, rgb(var(--color-cream-200)) 100%)`,
          }}
        />
        <div className="flex justify-between text-xs text-sage-400 mt-1">
          <span>{min}{unit}</span>
          <span>{max}{unit}</span>
        </div>
      </div>
    </div>
  )
}
