import React, { useState, useRef, useEffect } from 'react'
import { AudioLines, X, ChevronDown, User, AlertCircle } from 'lucide-react'
import { useVoiceProfiles } from '../../hooks/useVoiceProfiles'
import VoiceProfileForm from './VoiceProfileForm'
import VoiceProfileCard from './VoiceProfileCard'

const VoiceProfileManager: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data, isLoading, error, refetch } = useVoiceProfiles()
  const profileCount = data?.count || 0

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsExpanded(false)
      }
    }

    if (isExpanded) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isExpanded])

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Toggle Button - touch friendly */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`
          flex items-center space-x-2 px-4 py-2.5 min-h-11 rounded-lg transition-all
          ${isExpanded
            ? 'bg-sage-400 text-cream-50'
            : 'bg-sage-300 text-cream-50 hover:bg-sage-400'
          }
        `}
      >
        <AudioLines className="w-5 h-5" />
        <span className="font-medium hidden sm:inline">Voices</span>

        {profileCount > 0 && (
          <span className="ml-1 px-2 py-0.5 bg-sage-500 rounded-full text-xs">
            {profileCount}
          </span>
        )}

        <ChevronDown
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown Panel - responsive width */}
      {isExpanded && (
        <div className="fixed inset-x-4 top-20 sm:absolute sm:inset-x-auto sm:top-auto sm:mt-2 sm:right-0 sm:w-96 max-w-[400px] bg-white rounded-lg shadow-flat border border-cream-200 overflow-hidden z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-cream-50 border-b border-cream-200">
            <div className="flex items-center space-x-2">
              <AudioLines className="w-5 h-5 text-sage-400" />
              <h3 className="font-semibold text-forest-700">Voice Profiles</h3>
              {profileCount > 0 && (
                <span className="text-xs text-sage-500">
                  ({profileCount})
                </span>
              )}
            </div>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-2 min-h-11 min-w-11 text-sage-400 hover:text-forest-600 hover:bg-cream-100 rounded-lg transition-colors flex items-center justify-center"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Create Voice Profile Form */}
          <VoiceProfileForm onProfileCreated={refetch} />

          {/* Profile List - responsive height */}
          <div className="max-h-[50vh] sm:max-h-96 overflow-y-auto">
            {isLoading ? (
              <div className="p-8 text-center">
                <div className="w-8 h-8 border-3 border-sage-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-sm text-sage-500">Loading profiles...</p>
              </div>
            ) : error ? (
              <div className="p-8 text-center">
                <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
                <p className="text-sm text-red-600 mb-2">Failed to load profiles</p>
                <button
                  onClick={() => refetch()}
                  className="text-xs text-forest-600 hover:underline"
                >
                  Try again
                </button>
              </div>
            ) : !data?.profiles?.length ? (
              <div className="p-8 text-center">
                <User className="w-12 h-12 text-cream-300 mx-auto mb-3" />
                <p className="text-sm font-medium text-forest-600 mb-1">No voice profiles</p>
                <p className="text-xs text-sage-400 mb-4">
                  Register voice profiles to identify speakers in transcripts
                </p>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {data.profiles.map((profile) => (
                  <VoiceProfileCard
                    key={profile.profile_id}
                    profile={profile}
                    onRefresh={refetch}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer with instructions */}
          <div className="px-4 py-3 bg-cream-50 border-t border-cream-200">
            <p className="text-xs text-sage-500">
              Upload or record 5-30 seconds of clear speech for best results.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default VoiceProfileManager
