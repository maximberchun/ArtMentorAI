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
  score: number | null
  rubric_anchors: string[]
  prioritized_issues: PrioritizedIssue[]
  root_causes: string[]
  targeted_drills: TargetedDrill[]
  readiness_gate: string
  confidence: number
}

export type PrioritizedIssue = {
  title: string
  diagnosis: string
  priority: number
}

export type TargetedDrill = {
  name: string
  objective: string
  success_check: string
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
  rubric_anchors: string[]
  prioritized_issues: PrioritizedIssue[]
  root_causes: string[]
  targeted_drills: TargetedDrill[]
  readiness_gate: string | null
  confidence: number | null
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
  dimension_scores: Record<string, number | string | null>
  narrative: string | null
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
