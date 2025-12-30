import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Pencil, Check, X, ChevronDown } from 'lucide-react'
import { useVoiceProfiles } from '../../hooks/useVoiceProfiles'
import { useUpdateSpeaker } from '../../hooks/useUpdateSpeaker'

interface SpeakerEditorProps {
  transcriptionId: number
  currentSpeaker: string | null
  speakerConfidence?: number
}

const SpeakerEditor: React.FC<SpeakerEditorProps> = ({
  transcriptionId,
  currentSpeaker,
  speakerConfidence,
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [inputValue, setInputValue] = useState(currentSpeaker || '')
  const [showDropdown, setShowDropdown] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLSpanElement>(null)

  const { data: profilesData } = useVoiceProfiles()
  const updateSpeaker = useUpdateSpeaker()

  const profiles = profilesData?.profiles || []

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const handleCancel = useCallback(() => {
    setIsEditing(false)
    setShowDropdown(false)
    setInputValue(currentSpeaker || '')
  }, [currentSpeaker])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        if (isEditing) {
          handleCancel()
        }
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isEditing, handleCancel])

  const handleStartEdit = () => {
    setInputValue(currentSpeaker || '')
    setIsEditing(true)
    setShowDropdown(true)
  }

  const handleSave = async () => {
    if (!inputValue.trim()) {
      handleCancel()
      return
    }

    // Find matching profile if selecting from dropdown
    const matchingProfile = profiles.find(
      (p) => p.display_name === inputValue || p.name === inputValue
    )

    try {
      await updateSpeaker.mutateAsync({
        transcription_id: transcriptionId,
        speaker_name: inputValue.trim(),
        speaker_id: matchingProfile?.profile_id ?? null,
      })
      setIsEditing(false)
      setShowDropdown(false)
    } catch (error) {
      console.error('Failed to update speaker:', error)
    }
  }

  const handleSelectProfile = (profile: (typeof profiles)[0]) => {
    setInputValue(profile.display_name || profile.name)
    setShowDropdown(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }

  // Filter profiles based on input
  const filteredProfiles = profiles.filter((p) =>
    (p.display_name || p.name).toLowerCase().includes(inputValue.toLowerCase())
  )

  if (!isEditing) {
    return (
      <span className="inline-flex items-center gap-1 group">
        <span className="font-semibold text-sage-600">
          [{currentSpeaker || 'Unknown'}]
        </span>
        {speakerConfidence !== undefined && speakerConfidence < 1.0 && (
          <span className="text-xs text-sage-400">
            ({Math.round(speakerConfidence * 100)}%)
          </span>
        )}
        <button
          onClick={handleStartEdit}
          className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-cream-200 transition-opacity min-h-6 min-w-6 flex items-center justify-center"
          title="Edit speaker"
        >
          <Pencil className="w-3 h-3 text-sage-500" />
        </button>
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1 relative" ref={containerRef}>
      <span className="text-sage-600">[</span>
      <div className="relative">
        <div className="flex items-center gap-0.5">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value)
              setShowDropdown(true)
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowDropdown(true)}
            className="w-28 px-1.5 py-0.5 text-sm border border-forest-300 rounded focus:outline-none focus:ring-1 focus:ring-forest-500 bg-white"
            placeholder="Speaker name"
          />
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="p-0.5 rounded hover:bg-cream-200 min-h-6 min-w-6 flex items-center justify-center"
            title="Show profiles"
            type="button"
          >
            <ChevronDown className="w-3 h-3 text-sage-500" />
          </button>
        </div>

        {/* Dropdown menu */}
        {showDropdown && (
          <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-cream-200 rounded-lg shadow-lg z-20 max-h-48 overflow-y-auto">
            {filteredProfiles.length > 0 ? (
              <>
                <div className="px-2 py-1 text-xs text-sage-400 border-b border-cream-100 bg-cream-50">
                  Registered Profiles
                </div>
                {filteredProfiles.map((profile) => (
                  <button
                    key={profile.profile_id}
                    onClick={() => handleSelectProfile(profile)}
                    className="w-full px-2 py-1.5 text-left text-sm hover:bg-cream-100 flex items-center justify-between"
                    type="button"
                  >
                    <span className="text-forest-700">{profile.display_name || profile.name}</span>
                    <span className="text-xs text-sage-400">@{profile.name}</span>
                  </button>
                ))}
              </>
            ) : inputValue ? (
              <div className="px-2 py-2 text-xs text-sage-400">
                No matching profiles. Press Enter to use custom name.
              </div>
            ) : (
              <div className="px-2 py-2 text-xs text-sage-400">
                Type to search or enter custom name
              </div>
            )}
          </div>
        )}
      </div>
      <span className="text-sage-600">]</span>

      <button
        onClick={handleSave}
        disabled={updateSpeaker.isPending}
        className="p-0.5 rounded hover:bg-green-100 text-green-600 min-h-6 min-w-6 flex items-center justify-center disabled:opacity-50"
        title="Save"
        type="button"
      >
        <Check className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={handleCancel}
        className="p-0.5 rounded hover:bg-red-100 text-red-600 min-h-6 min-w-6 flex items-center justify-center"
        title="Cancel"
        type="button"
      >
        <X className="w-3.5 h-3.5" />
      </button>

      {/* Loading indicator */}
      {updateSpeaker.isPending && (
        <span className="text-xs text-sage-400 ml-1">Saving...</span>
      )}
    </span>
  )
}

export default SpeakerEditor
