import { CSSProperties } from 'react'

export type VisualElementKey =
  | 'navLogo'
  | 'menuContent'
  | 'menuGuitar'
  | 'studioIndex'
  | 'studioGuitar'
  | 'studioContent'

export interface VisualTransform {
  x: number
  y: number
  scale: number
  rotation: number
  zIndex: number
}

export type VisualConfig = Record<VisualElementKey, VisualTransform>

export const VISUAL_ELEMENT_LABELS: Record<VisualElementKey, string> = {
  navLogo: 'Navigation logo',
  menuContent: 'Menu content',
  menuGuitar: 'Menu guitar',
  studioIndex: 'Studio number',
  studioGuitar: 'Studio guitar',
  studioContent: 'Studio controls',
}

export const DEFAULT_VISUAL_CONFIG: VisualConfig = {
  navLogo: { x: 0, y: 0, scale: 1.15, rotation: 0, zIndex: 10 },
  menuContent: { x: 0, y: 0, scale: 1, rotation: 0, zIndex: 2 },
  menuGuitar: { x: 0, y: 0, scale: 1, rotation: 0, zIndex: 1 },
  studioIndex: { x: 0, y: 0, scale: 1, rotation: 0, zIndex: 0 },
  studioGuitar: { x: 0, y: 0, scale: 1, rotation: 0, zIndex: 1 },
  studioContent: { x: 0, y: 0, scale: 1, rotation: 0, zIndex: 2 },
}

export function visualStyle(transform: VisualTransform): CSSProperties {
  return {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0) scale(${transform.scale}) rotate(${transform.rotation}deg)`,
    zIndex: transform.zIndex,
  }
}

export function mergeVisualConfig(value: unknown): VisualConfig {
  if (!value || typeof value !== 'object') return DEFAULT_VISUAL_CONFIG
  const stored = value as Partial<VisualConfig>
  return Object.fromEntries(
    Object.entries(DEFAULT_VISUAL_CONFIG).map(([key, defaults]) => [
      key,
      { ...defaults, ...(stored[key as VisualElementKey] || {}) },
    ]),
  ) as VisualConfig
}
