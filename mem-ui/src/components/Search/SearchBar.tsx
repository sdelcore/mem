import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Search, X, Clock } from 'lucide-react'
import { debounce } from '../../utils/debounce'
import { API_BASE_URL } from '../../utils/config'

interface SearchResult {
  id: string
  timestamp: Date
  text: string
  type: 'transcript' | 'annotation'
  highlight?: string
}

interface SearchBarProps {
  placeholder?: string
  onSearch: (query: string) => void
  onResultClick?: (timestamp: Date) => void
}

const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = 'Search...',
  onSearch,
  onResultClick,
}) => {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<SearchResult[]>([])
  const [showResults, setShowResults] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const searchRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Store onSearch in a ref to avoid recreating debounced function
  const onSearchRef = useRef(onSearch)
  onSearchRef.current = onSearch

  // Debounced search function - use useMemo to avoid recreating on every render
  const debouncedSearch = useMemo(
    () => debounce(async (searchQuery: string) => {
      if (searchQuery.trim().length < 2) {
        setResults([])
        setShowResults(false)
        return
      }

      setIsSearching(true)
      onSearchRef.current(searchQuery)

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/search?type=transcript&q=${encodeURIComponent(searchQuery)}`
        )

        if (!response.ok) {
          throw new Error('Search failed')
        }

        const data = await response.json()
        const searchResults: SearchResult[] = data.results.map((item: any) => ({
          id: item.id,
          timestamp: new Date(item.timestamp),
          text: item.text,
          type: item.type,
          highlight: item.highlight,
        }))

        setResults(searchResults)
        setShowResults(true)  // Show results dropdown even if empty (to show "no results" message)
        setSelectedIndex(-1)
      } catch (error) {
        console.error('Search error:', error)
        setResults([])
        setShowResults(false)
      } finally {
        setIsSearching(false)
      }
    }, 300),
    [] // Empty deps - function is stable
  )

  useEffect(() => {
    debouncedSearch(query)
  }, [query, debouncedSearch])

  // Handle clicks outside to close results
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const handleClear = () => {
    setQuery('')
    setResults([])
    setShowResults(false)
    setSelectedIndex(-1)
    inputRef.current?.focus()
  }

  const handleResultClick = (result: SearchResult) => {
    if (onResultClick) {
      onResultClick(result.timestamp)
    }
    setShowResults(false)
    // Keep query visible so user can see what they searched for
    // They can clear manually with the X button
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults || results.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) => 
          prev < results.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < results.length) {
          handleResultClick(results[selectedIndex])
        }
        break
      case 'Escape':
        setShowResults(false)
        setSelectedIndex(-1)
        break
    }
  }

  const highlightText = (text: string, highlight?: string) => {
    if (!highlight) return text

    const parts = text.split(new RegExp(`(${highlight})`, 'gi'))
    return parts.map((part, index) =>
      part.toLowerCase() === highlight.toLowerCase() ? (
        <mark key={index} className="bg-cream-300 font-medium">
          {part}
        </mark>
      ) : (
        part
      )
    )
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  return (
    <div ref={searchRef} className="relative w-full sm:max-w-sm">
      {/* Search input - touch friendly */}
      <div className="relative group">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-sage-400 w-5 h-5 transition-colors group-focus-within:text-forest-500" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full pl-10 pr-10 py-2.5 min-h-11 bg-cream-100 border border-cream-200 rounded-lg text-sm text-forest-700 focus:outline-none focus:ring-2 focus:ring-sage-300/30 focus:border-sage-300 focus:bg-white transition-colors duration-150"
        />
        {query && !isSearching && (
          <button
            onClick={handleClear}
            className="absolute right-1 top-1/2 transform -translate-y-1/2 text-sage-400 hover:text-forest-600 p-2 min-h-9 min-w-9 rounded-lg hover:bg-cream-100 transition-colors flex items-center justify-center"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        {isSearching && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            <div className="relative">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-cream-200"></div>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-transparent border-t-sage-300 absolute top-0"></div>
            </div>
          </div>
        )}
      </div>

      {/* Search results dropdown - responsive height */}
      {showResults && results.length > 0 && (
        <div className="absolute top-full mt-2 w-full bg-white border border-cream-200 rounded-lg shadow-flat max-h-[60vh] sm:max-h-96 overflow-y-auto z-50">
          {results.map((result, index) => (
            <div
              key={result.id}
              className={`px-4 py-3 min-h-14 border-b border-cream-200 hover:bg-cream-50 cursor-pointer transition-colors active:bg-cream-100 ${
                index === selectedIndex ? 'bg-sage-50' : ''
              }`}
              onClick={() => handleResultClick(result)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Clock className="w-4 h-4 text-sage-400" />
                    <span className="text-sm text-forest-600">
                      {formatTimestamp(result.timestamp)}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        result.type === 'transcript'
                          ? 'bg-sage-50 text-sage-500'
                          : 'bg-cream-200 text-sage-400'
                      }`}
                    >
                      {result.type}
                    </span>
                  </div>
                  <p className="text-sm text-forest-700 line-clamp-2">
                    {highlightText(result.text, result.highlight || query)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No results message */}
      {showResults && results.length === 0 && query.trim().length >= 2 && !isSearching && (
        <div className="absolute top-full mt-2 w-full bg-white border border-cream-200 rounded-lg shadow-flat p-4 z-50">
          <p className="text-sm text-sage-500 text-center mb-2">
            No results found for "{query}"
          </p>
          <p className="text-xs text-sage-400 text-center">
            Try shorter keywords or check spelling
          </p>
        </div>
      )}
    </div>
  )
}

export default SearchBar