import React from 'react'
import { AlertTriangle } from 'lucide-react'

interface SettingSectionProps {
  title: string
  description?: string
  requiresRestart?: boolean
  children: React.ReactNode
}

export const SettingSection: React.FC<SettingSectionProps> = ({
  title,
  description,
  requiresRestart,
  children,
}) => {
  return (
    <div className="bg-white rounded-lg shadow-flat border border-cream-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-cream-200 bg-cream-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-forest-700">{title}</h3>
            {description && (
              <p className="text-sm text-sage-500 mt-1">{description}</p>
            )}
          </div>
          {requiresRestart && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-100 text-amber-700 rounded-lg text-sm">
              <AlertTriangle className="w-4 h-4" />
              <span>Requires Restart</span>
            </div>
          )}
        </div>
      </div>
      <div className="p-6 space-y-6">{children}</div>
    </div>
  )
}
