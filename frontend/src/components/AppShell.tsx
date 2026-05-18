import { ReactNode, useState } from 'react'
import { Session } from '@supabase/supabase-js'
import { Link, useLocation } from 'react-router-dom'

type AppShellProps = {
  session: Session | null
  onSignOut: () => Promise<void>
  children: ReactNode
}

function NavLink({ to, children }: { to: string; children: ReactNode }) {
  const location = useLocation()
  const isActive = location.pathname === to

  return (
    <Link
      to={to}
      className={`relative px-3 py-2 text-sm font-medium transition-colors ${
        isActive
          ? 'text-foreground'
          : 'text-muted-foreground hover:text-foreground'
      }`}
    >
      {children}
      {isActive && (
        <span className="absolute bottom-0 left-3 right-3 h-0.5 rounded-full bg-primary" />
      )}
    </Link>
  )
}

function MobileNavLink({ to, children, onClick }: { to: string; children: ReactNode; onClick?: () => void }) {
  const location = useLocation()
  const isActive = location.pathname === to

  return (
    <Link
      to={to}
      onClick={onClick}
      className={`block px-4 py-3 text-sm font-medium transition-colors ${
        isActive
          ? 'bg-secondary text-foreground'
          : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
      }`}
    >
      {children}
    </Link>
  )
}

function LockedNavLink({ to, label }: { to: string; label: string }) {
  const signInTo = `/sign-in?next=${encodeURIComponent(to)}`
  return (
    <Link
      to={signInTo}
      className="relative px-3 py-2 text-sm font-medium text-muted-foreground/70 transition-colors hover:text-muted-foreground"
      title="Sign in required"
    >
      {label}
    </Link>
  )
}

function LockedMobileNavLink({ to, label, onClick }: { to: string; label: string; onClick?: () => void }) {
  const signInTo = `/sign-in?next=${encodeURIComponent(to)}`
  return (
    <Link
      to={signInTo}
      onClick={onClick}
      className="block px-4 py-3 text-sm font-medium text-muted-foreground/70 hover:bg-secondary hover:text-muted-foreground"
    >
      {label} <span className="text-xs">(sign in)</span>
    </Link>
  )
}

export function AppShell({ session, onSignOut, children }: AppShellProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 lg:px-6">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                <svg
                  className="h-5 w-5 text-primary-foreground"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42"
                  />
                </svg>
              </div>
              <span className="text-lg font-semibold tracking-tight">ArtMentorAI</span>
            </Link>

            <nav className="hidden items-center md:flex">
              <NavLink to="/">Home</NavLink>
              <NavLink to="/critique">Critique</NavLink>
              <NavLink to="/conversation">Chat</NavLink>
              {session ? (
                <>
                  <NavLink to="/portfolio">Portfolio</NavLink>
                  <NavLink to="/history">History</NavLink>
                  <NavLink to="/progress">Progress</NavLink>
                  <NavLink to="/profile">Profile</NavLink>
                </>
              ) : (
                <>
                  <LockedNavLink to="/portfolio" label="Portfolio" />
                  <LockedNavLink to="/history" label="History" />
                  <LockedNavLink to="/progress" label="Progress" />
                  <LockedNavLink to="/profile" label="Profile" />
                </>
              )}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-3 md:flex">
              {session ? (
                <>
                  <span className="text-sm text-muted-foreground">{session.user.email}</span>
                  <button
                    type="button"
                    className="rounded-lg border border-border bg-secondary px-3 py-1.5 text-sm font-medium text-secondary-foreground transition-colors hover:bg-border"
                    onClick={() => void onSignOut()}
                  >
                    Sign out
                  </button>
                </>
              ) : (
                <Link
                  to="/sign-in"
                  className="rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                >
                  Sign in
                </Link>
              )}
            </div>

            <button
              type="button"
              className="rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                {mobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="border-t border-border md:hidden">
            <nav className="divide-y divide-border">
              <MobileNavLink to="/" onClick={() => setMobileMenuOpen(false)}>Home</MobileNavLink>
              <MobileNavLink to="/critique" onClick={() => setMobileMenuOpen(false)}>Critique</MobileNavLink>
              <MobileNavLink to="/conversation" onClick={() => setMobileMenuOpen(false)}>Chat</MobileNavLink>
              {session ? (
                <>
                  <MobileNavLink to="/portfolio" onClick={() => setMobileMenuOpen(false)}>Portfolio</MobileNavLink>
                  <MobileNavLink to="/history" onClick={() => setMobileMenuOpen(false)}>History</MobileNavLink>
                  <MobileNavLink to="/progress" onClick={() => setMobileMenuOpen(false)}>Progress</MobileNavLink>
                  <MobileNavLink to="/profile" onClick={() => setMobileMenuOpen(false)}>Profile</MobileNavLink>
                </>
              ) : (
                <>
                  <LockedMobileNavLink to="/portfolio" label="Portfolio" onClick={() => setMobileMenuOpen(false)} />
                  <LockedMobileNavLink to="/history" label="History" onClick={() => setMobileMenuOpen(false)} />
                  <LockedMobileNavLink to="/progress" label="Progress" onClick={() => setMobileMenuOpen(false)} />
                  <LockedMobileNavLink to="/profile" label="Profile" onClick={() => setMobileMenuOpen(false)} />
                </>
              )}
            </nav>
            <div className="border-t border-border p-4">
              {session ? (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">{session.user.email}</p>
                  <button
                    type="button"
                    className="w-full rounded-lg border border-border bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground"
                    onClick={() => {
                      void onSignOut()
                      setMobileMenuOpen(false)
                    }}
                  >
                    Sign out
                  </button>
                </div>
              ) : (
                <Link
                  to="/sign-in"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block w-full rounded-lg bg-primary px-4 py-2 text-center text-sm font-medium text-primary-foreground"
                >
                  Sign in
                </Link>
              )}
            </div>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 lg:px-6">{children}</main>
    </div>
  )
}
