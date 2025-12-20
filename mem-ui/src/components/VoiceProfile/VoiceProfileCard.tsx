import React from 'react'
import { User, Trash2 } from 'lucide-react'
import { format } from 'date-fns'
import { VoiceProfile, useDeleteVoiceProfile } from '../../hooks/useVoiceProfiles'

interface VoiceProfileCardProps {
  profile: VoiceProfile
  onRefresh: () => void
}

const VoiceProfileCard: React.FC<VoiceProfileCardProps> = ({ profile, onRefresh }) => {
  const deleteMutation = useDeleteVoiceProfile()

  const handleDelete = async () => {
    if (window.confirm(`Delete voice profile "${profile.display_name || profile.name}"?`)) {
      try {
        await deleteMutation.mutateAsync(profile.profile_id)
        onRefresh()
      } catch (error) {
        console.error('Failed to delete profile:', error)
      }
    }
  }

  return (
    <div className="p-3 bg-cream-50 rounded-lg border border-cream-200">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-sage-200 rounded-full flex items-center justify-center">
            <User className="w-5 h-5 text-sage-500" />
          </div>
          <div>
            <p className="font-medium text-forest-700">
              {profile.display_name || profile.name}
            </p>
            <p className="text-xs text-sage-500">@{profile.name}</p>
            <p className="text-xs text-sage-400">
              Added {format(new Date(profile.created_at), 'MMM d, yyyy')}
            </p>
          </div>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleteMutation.isPending}
          className="p-2 text-sage-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
          title="Delete profile"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

export default VoiceProfileCard
