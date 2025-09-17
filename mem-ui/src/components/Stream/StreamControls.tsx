import React, { useState } from 'react'
import { Plus, Camera, X } from 'lucide-react'
import { useCreateStream } from '../../hooks/useStreams'

interface StreamControlsProps {
  onStreamCreated?: () => void
}

const StreamControls: React.FC<StreamControlsProps> = ({ onStreamCreated }) => {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [streamName, setStreamName] = useState('')
  
  const createMutation = useCreateStream()

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync({
        name: streamName || undefined,
        metadata: {
          source: 'OBS Studio',
          created_from: 'Web UI'
        }
      })
      
      setStreamName('')
      setShowCreateForm(false)
      onStreamCreated?.()
    } catch (error) {
      console.error('Failed to create stream:', error)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !createMutation.isPending) {
      handleCreate()
    }
  }

  return (
    <div className="border-b border-cream-200 p-4">
      {!showCreateForm ? (
        <button
          onClick={() => setShowCreateForm(true)}
          className="w-full flex items-center justify-center space-x-2 py-2 px-4 bg-forest-500 text-cream-50 rounded-lg hover:bg-forest-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm font-medium">Create New Stream</span>
        </button>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-forest-700">New Stream Session</h3>
            <button
              onClick={() => {
                setShowCreateForm(false)
                setStreamName('')
              }}
              className="text-sage-400 hover:text-forest-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <input
            type="text"
            placeholder="Stream name (optional)"
            value={streamName}
            onChange={(e) => setStreamName(e.target.value)}
            onKeyPress={handleKeyPress}
            className="w-full px-3 py-2 text-sm border border-cream-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-500 focus:border-transparent"
            autoFocus
          />
          
          <div className="flex space-x-2">
            <button
              onClick={handleCreate}
              disabled={createMutation.isPending}
              className="flex-1 flex items-center justify-center space-x-2 py-2 px-4 bg-forest-500 text-cream-50 rounded-lg hover:bg-forest-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-cream-50 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm">Creating...</span>
                </>
              ) : (
                <>
                  <Camera className="w-4 h-4" />
                  <span className="text-sm">Create Stream</span>
                </>
              )}
            </button>
            
            <button
              onClick={() => {
                setShowCreateForm(false)
                setStreamName('')
              }}
              className="px-4 py-2 text-sm text-sage-600 bg-cream-100 rounded-lg hover:bg-cream-200 transition-colors"
            >
              Cancel
            </button>
          </div>

          {createMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-xs text-red-600">
                {createMutation.error?.message || 'Failed to create stream'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default StreamControls