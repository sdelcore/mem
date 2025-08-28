# Mem UI Frontend Components Documentation

## Overview
This document describes the React components for the Mem video tracking system UI. The frontend provides an interactive timeline view for reviewing captured video data, uploading new videos, and searching through transcripts.

## Core Components

### 1. Timeline Component
**Location**: `src/components/Timeline/Timeline.tsx`

Interactive timeline visualization showing video data over time with color-coded segments.

#### Features
- **Default View**: Last 12 hours of data
- **Color Coding**: 
  - Grey: No content/data
  - Blue: Frame images present
  - Green: Transcriptions present
  - Purple: Both frames and transcripts
  - Orange: Annotations present
- **Interactions**:
  - Hover: Shows frame thumbnail preview
  - Click: Navigates to specific time
  - Click & Drag: Selects time range
- **Zoom Controls**: Adjustable timeline scale

#### Props
```typescript
interface TimelineProps {
  startTime?: Date;        // Default: 12 hours ago
  endTime?: Date;          // Default: now
  onTimeSelect?: (time: Date) => void;
  onRangeSelect?: (start: Date, end: Date) => void;
  data?: TimelineData[];   // Timeline data from API
}
```

#### Usage Example
```tsx
<Timeline
  startTime={new Date(Date.now() - 12 * 60 * 60 * 1000)}
  endTime={new Date()}
  onTimeSelect={(time) => console.log('Selected time:', time)}
  onRangeSelect={(start, end) => console.log('Selected range:', start, end)}
/>
```

### 2. VideoUpload Component
**Location**: `src/components/Upload/VideoUpload.tsx`

Drag-and-drop video upload interface with filename validation and progress tracking.

#### Features
- **Drag & Drop**: Intuitive file upload interface
- **Validation**: 
  - Only accepts `.mkv` files
  - Validates filename format: `YYYY-MM-DD_HH-MM-SS.mkv`
  - Max file size: 5GB
- **Progress Tracking**: Visual upload progress bar
- **Error Messages**: Clear validation feedback
- **Job Monitoring**: Polls job status after upload

#### Props
```typescript
interface VideoUploadProps {
  onUploadSuccess?: (jobId: string) => void;
  onUploadError?: (error: string) => void;
  onUploadProgress?: (progress: number) => void;
}
```

#### Error Messages
- Invalid format: "Invalid file format. File must be named YYYY-MM-DD_HH-MM-SS.mkv"
- Wrong extension: "Invalid file extension. File must be .mkv format"
- File too large: "File size exceeds maximum allowed size of 5GB"

#### Usage Example
```tsx
<VideoUpload
  onUploadSuccess={(jobId) => console.log('Upload successful, job:', jobId)}
  onUploadError={(error) => alert(error)}
  onUploadProgress={(progress) => console.log(`Upload: ${progress}%`)}
/>
```

### 3. SearchBar Component
**Location**: `src/components/Search/SearchBar.tsx`

Text search interface for finding content in transcripts with debouncing and result highlighting.

#### Features
- **Debounced Search**: 300ms delay to reduce API calls
- **Result Highlighting**: Highlights matches on timeline
- **Click to Navigate**: Jump to search result timestamps
- **Loading States**: Shows search in progress
- **Empty States**: Clear messaging when no results

#### Props
```typescript
interface SearchBarProps {
  onSearch?: (query: string) => void;
  onResultClick?: (timestamp: Date) => void;
  placeholder?: string;
  debounceMs?: number;     // Default: 300
}
```

#### Usage Example
```tsx
<SearchBar
  placeholder="Search transcripts..."
  onSearch={(query) => searchAPI(query)}
  onResultClick={(timestamp) => navigateToTime(timestamp)}
/>
```

### 4. ContentViewer Component
**Location**: `src/components/Content/ContentViewer.tsx`

Displays content (frames, transcripts, annotations) for selected time or time range.

#### Features
- **Frame Display**: Shows video frames with zoom capability
- **Transcript Display**: Formatted text with timestamps
- **Annotation Display**: User notes and AI-generated content
- **Gallery View**: Multiple frames in grid layout
- **Export Options**: Save frames or copy text

#### Props
```typescript
interface ContentViewerProps {
  startTime: Date;
  endTime?: Date;           // If not provided, shows single time point
  content?: ContentData[];  // Frames, transcripts, annotations
  layout?: 'vertical' | 'horizontal' | 'grid';
}
```

#### Usage Example
```tsx
<ContentViewer
  startTime={selectedTime}
  endTime={selectedEndTime}
  content={timelineData}
  layout="vertical"
/>
```

### 5. TimelineSegment Component
**Location**: `src/components/Timeline/TimelineSegment.tsx`

Individual segment within the timeline representing a specific time period.

#### Features
- **Color Indication**: Based on content type
- **Hover Preview**: Shows thumbnail on hover
- **Click Handler**: Triggers time selection
- **Density Indicator**: Shows amount of content

#### Props
```typescript
interface TimelineSegmentProps {
  timestamp: Date;
  hasFrame: boolean;
  hasTranscript: boolean;
  hasAnnotation: boolean;
  frameUrl?: string;
  onClick?: () => void;
  onHover?: (hovering: boolean) => void;
}
```

### 6. PreviewTooltip Component
**Location**: `src/components/Timeline/PreviewTooltip.tsx`

Tooltip that appears on timeline hover showing frame preview and metadata.

#### Features
- **Frame Thumbnail**: Small preview image
- **Timestamp Display**: Exact time
- **Content Indicators**: Icons for available content types
- **Smart Positioning**: Stays within viewport

#### Props
```typescript
interface PreviewTooltipProps {
  visible: boolean;
  x: number;
  y: number;
  timestamp: Date;
  frameUrl?: string;
  hasTranscript: boolean;
  hasAnnotation: boolean;
}
```

## Data Types

### TimelineData
```typescript
interface TimelineData {
  timestamp: Date;
  source_id: number;
  frame?: {
    frame_id: number;
    url: string;
    perceptual_hash: string;
  };
  transcript?: {
    text: string;
    confidence: number;
    language: string;
  };
  annotations?: Array<{
    type: string;
    content: string;
    created_by: string;
  }>;
  scene_changed: boolean;
}
```

### ContentData
```typescript
interface ContentData {
  type: 'frame' | 'transcript' | 'annotation';
  timestamp: Date;
  data: any;  // Specific to content type
}
```

## Hooks

### useTimeline
**Location**: `src/hooks/useTimeline.ts`

Custom hook for timeline data fetching and management.

```typescript
function useTimeline(startTime: Date, endTime: Date) {
  // Returns timeline data, loading state, error state
  return { data, isLoading, error, refetch };
}
```

### useSearch
**Location**: `src/hooks/useSearch.ts`

Custom hook for transcript search functionality.

```typescript
function useSearch(query: string, debounceMs: number = 300) {
  // Returns search results, loading state
  return { results, isSearching, error };
}
```

### useUpload
**Location**: `src/hooks/useUpload.ts`

Custom hook for file upload with progress tracking.

```typescript
function useUpload() {
  // Returns upload function, progress, status
  return { upload, progress, status, error };
}
```

## Environment Configuration

The frontend requires environment variables to be set in a `.env` file:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# Optional Configuration
VITE_TIMELINE_DEFAULT_HOURS=12
VITE_UPLOAD_MAX_SIZE_GB=5
VITE_SEARCH_DEBOUNCE_MS=300
```

## Styling Guidelines

### Color Palette
```css
/* Timeline segment colors */
--color-no-content: #e5e7eb;     /* grey-200 */
--color-frame: #3b82f6;          /* blue-500 */
--color-transcript: #10b981;     /* green-500 */
--color-both: #8b5cf6;           /* purple-500 */
--color-annotation: #f97316;     /* orange-500 */

/* UI colors */
--color-background: #ffffff;
--color-text: #1f2937;
--color-border: #d1d5db;
--color-hover: #f3f4f6;
```

### Responsive Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

## Performance Considerations

### Timeline Optimization
- Use Canvas or WebGL for rendering large datasets
- Virtualize timeline segments (only render visible portion)
- Implement progressive loading for long time ranges
- Cache frame thumbnails in memory

### Upload Optimization
- Stream large files instead of loading into memory
- Show accurate progress using XMLHttpRequest progress events
- Implement chunked upload for files > 100MB

### Search Optimization
- Debounce user input (300ms default)
- Cache search results
- Implement pagination for large result sets
- Use React Query for intelligent caching

## Testing Guidelines

### Component Tests
- Use React Testing Library for component testing
- Mock API calls with MSW (Mock Service Worker)
- Test user interactions (click, drag, hover)
- Test error states and loading states

### Integration Tests
- Test complete user flows (upload → process → view)
- Test timeline navigation with real data
- Test search functionality with various queries

## Accessibility

### ARIA Labels
- All interactive elements must have proper ARIA labels
- Timeline segments should announce content type
- Upload area should announce drag-and-drop capability

### Keyboard Navigation
- Tab through all interactive elements
- Arrow keys for timeline navigation
- Enter/Space for selection
- Escape to cancel operations

### Screen Reader Support
- Announce timeline position changes
- Read transcript content
- Announce upload progress

## Browser Support

### Minimum Requirements
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Required Features
- ES2020 JavaScript
- CSS Grid and Flexbox
- Canvas API
- File API
- WebSocket (future)