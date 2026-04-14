import { ReactNode } from 'react'
import { Session } from '@supabase/supabase-js'
import { Link } from 'react-router-dom'

type AppShellProps = {
  session: Session | null
  onSignOut: () => Promise<void>
  children: ReactNode
}

export function AppShell({ session, onSignOut, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <h1 className="text-lg font-semibold tracking-tight">ArtMentorAI</h1>
          <nav className="flex flex-wrap gap-3 text-sm text-stone-700">
            <Link to="/" className="hover:text-stone-900">
              Home
            </Link>
            <Link to="/profile" className="hover:text-stone-900">
              Profile
            </Link>
            <Link to="/critique" className="hover:text-stone-900">
              Critique
            </Link>
            <Link to="/portfolio" className="hover:text-stone-900">
              Portfolio
            </Link>
            <Link to="/history" className="hover:text-stone-900">
              History
            </Link>
            <Link to="/progress" className="hover:text-stone-900">
              Progress
            </Link>
          </nav>
          <div className="flex items-center gap-2 text-xs text-stone-600">
            <span>{session?.user.email ?? 'Not signed in'}</span>
            {session && (
              <button
                type="button"
                className="rounded-md border border-stone-300 bg-white px-2 py-1 hover:bg-stone-50"
                onClick={() => void onSignOut()}
              >
                Sign out
              </button>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  )
}
