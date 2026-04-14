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
  score: number
  technical_errors: string[]
  constructive_advice: string
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
