import { Image, FileText, Tag, Layers, Circle } from 'lucide-react'
import { LucideIcon } from 'lucide-react'

/**
 * Content type icon mapping for consistent accessibility across components.
 * Used to provide visual icons alongside colors for WCAG 2.1 AA compliance.
 */
export const CONTENT_ICONS: Record<string, LucideIcon> = {
  frame: Image,
  transcript: FileText,
  annotation: Tag,
  both: Layers,
  empty: Circle,
}

export const CONTENT_LABELS: Record<string, string> = {
  frame: 'Frame',
  transcript: 'Transcript',
  annotation: 'Annotation',
  both: 'Frame & Transcript',
  empty: 'No data',
}

/**
 * Get the icon component for a content type
 */
export function getContentIcon(type: keyof typeof CONTENT_ICONS): LucideIcon {
  return CONTENT_ICONS[type] || CONTENT_ICONS.empty
}

/**
 * Get the label for a content type
 */
export function getContentLabel(type: keyof typeof CONTENT_LABELS): string {
  return CONTENT_LABELS[type] || CONTENT_LABELS.empty
}
