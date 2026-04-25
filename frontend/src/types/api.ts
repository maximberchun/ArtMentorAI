export type AuthMe = {
  user_id: string
  email: string | null
  role: string
}

export type UserProfile = {
  user_id: string
  goals: string[]
  preferred_styles: string[]
  disliked_styles: string[]
  favorite_artists: string[]
  experience_level: string
  retain_memory: boolean
}

export type AnalysisResponse = {
  summary: string
  score: number | null
  technical_errors: string[]
  constructive_advice: string
}

export type ConversationInfo = {
  id: string
  title: string | null
  created_at: string | null
}

export type ConversationMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string | null
}

export type PortfolioHistoryItem = {
  id: string
  type: 'critique' | 'portfolio_item'
  user_id: string
  filename: string
  timestamp: string
  tags: string[]
  description: string | null
  score: number | null
  summary: string | null
  advice: string | null
  goals_snapshot: string | null
  level_estimate: number | null
  image_url: string | null
}

export type UploadResponse = {
  ids: string[]
}

export type ProgressSnapshotSummary = {
  id: string
  critique_id: string | null
  rubric_key: string
  aggregate_score: number | null
  created_at: string | null
}

export type ProgressMeResponse = {
  user_id: string
  total_xp: number
  current_level: number
  streak_count: number
  streak_last_date: string | null
  badges: string[]
  latest_snapshot: ProgressSnapshotSummary | null
  recent_snapshots: ProgressSnapshotSummary[]
}
