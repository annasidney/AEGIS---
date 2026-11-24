export type CoreState = 'IDLE' | 'LISTENING' | 'THINKING' | 'EXECUTING' | 'SPEAKING'

export interface User {
  id: number
  provider: string
  name: string
  email?: string | null
  picture?: string | null
  role: string
  initial: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'aegis' | 'system'
  text: string
  tool?: string | null
  route?: string
  latency?: number | null
  steps?: { tool: string }[]
  ts: number
}

export interface DetectionBox {
  id: number
  name: string
  confidence: number
  location: string
  spatial_relationship: string
  stable: boolean
  rel_x: number
  rel_y: number
  rel_w: number
  rel_h: number
}

export interface VisualMemoryItem {
  id: number
  object: string
  location_context: string
  room: string
  spatial_relationship: string | null
  confidence: number
  last_seen: string
  is_user_saved: boolean
}

export interface ReminderItem { id: number; text: string; time: string; raw_time: string }
export interface RoutineItem { id: number; action_type: string; target: string; time_of_day: string; frequency: number; auto_enabled: boolean }
export interface RoutineSuggestion { id: number; target: string; time_slot: string; frequency: number; message: string }
export interface MemoryEntry { id: number; key: string; value: string; category: string }

export interface StatusInfo {
  app_name: string
  version: string
  model: string
  vision_engine: string
  router_latency_ms: number | null
  last_latency_ms: number | null
  google_auth_enabled: boolean
  has_api_key: boolean
}

export interface SettingsInfo {
  GEMINI_MODEL: string
  LEARNING_ENABLED: boolean
  LOCATION_ENABLED: boolean
  VOICE_FIRST_MODE: boolean
  has_api_key: boolean
}

export interface A11yPrefs { contrast: boolean; dyslexic: boolean; reduceMotion: boolean; textScale: number }

declare global {
  interface Window { google?: any }
}
