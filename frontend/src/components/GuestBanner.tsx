import { Link, useLocation } from 'react-router-dom'

export function GuestBanner() {
  const location = useLocation()
  const signInTo = `/sign-in?next=${encodeURIComponent(location.pathname)}`

  return (
    <div className="mb-6 rounded-lg border border-border bg-secondary/50 px-4 py-3 text-sm text-muted-foreground">
      <span>
        You are using ArtMentorAI as a guest. Critiques and chat are not saved.{' '}
        <Link to={signInTo} className="font-medium text-primary hover:text-primary/90">
          Sign in
        </Link>{' '}
        to save your work and track progress.
      </span>
    </div>
  )
}
