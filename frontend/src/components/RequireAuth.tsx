import { ReactNode } from 'react'
import { Session } from '@supabase/supabase-js'
import { Navigate } from 'react-router-dom'

type RequireAuthProps = {
  session: Session | null
  children: ReactNode
}

export function RequireAuth({ session, children }: RequireAuthProps) {
  const nowInSeconds = Math.floor(Date.now() / 1000)
  const isExpired = typeof session?.expires_at === 'number' && session.expires_at <= nowInSeconds

  if (!session || isExpired) return <Navigate to="/sign-in" replace />
  return <>{children}</>
}
