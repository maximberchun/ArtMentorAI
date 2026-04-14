import { ReactNode } from 'react'
import { Session } from '@supabase/supabase-js'
import { Navigate } from 'react-router-dom'

type RequireAuthProps = {
  session: Session | null
  children: ReactNode
}

export function RequireAuth({ session, children }: RequireAuthProps) {
  if (!session) return <Navigate to="/sign-in" replace />
  return <>{children}</>
}
