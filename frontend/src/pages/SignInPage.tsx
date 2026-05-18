import { FormEvent, useEffect, useRef, useState } from 'react'
import { Session } from '@supabase/supabase-js'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { supabase } from '../lib/supabase'

type SignInPageProps = {
  session: Session | null
}

function safeReturnPath(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//')) {
    return '/'
  }
  return next
}

export function SignInPage({ session }: SignInPageProps) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnTo = safeReturnPath(searchParams.get('next'))
  const formRef = useRef<HTMLFormElement>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState<'signin' | 'signup' | 'google' | null>(null)

  useEffect(() => {
    if (session) {
      void navigate(returnTo, { replace: true })
    }
  }, [navigate, returnTo, session])

  async function signInEmail(e: FormEvent) {
    e.preventDefault()
    setMessage(null)
    if (!supabase) {
      setMessage('Missing Supabase env vars.')
      return
    }
    setBusy('signin')
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) setMessage(error.message)
    } finally {
      setBusy(null)
    }
  }

  async function signUpEmail() {
    const form = formRef.current
    if (form && !form.checkValidity()) {
      form.reportValidity()
      return
    }
    if (!supabase) {
      setMessage('Missing Supabase env vars.')
      return
    }
    setBusy('signup')
    setMessage(null)
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/sign-in` },
      })
      if (error) {
        setMessage(error.message)
        return
      }
      if (!data.session) {
        setMessage('Account created. Confirm your email before signing in.')
      }
    } finally {
      setBusy(null)
    }
  }

  async function signInGoogle() {
    if (!supabase) {
      setMessage('Missing Supabase env vars.')
      return
    }
    setBusy('google')
    setMessage(null)
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: `${window.location.origin}/sign-in` },
      })
      if (error) setMessage(error.message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <svg
              className="h-7 w-7 text-primary-foreground"
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
          <h2 className="text-2xl font-bold text-foreground">Welcome back</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to continue to ArtMentorAI
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <form ref={formRef} className="space-y-4" onSubmit={signInEmail}>
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-foreground">
                Email
              </label>
              <input
                id="email"
                className="w-full rounded-lg border border-input bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(ev) => setEmail(ev.target.value)}
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-foreground">
                Password
              </label>
              <input
                id="password"
                className="w-full rounded-lg border border-input bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                minLength={6}
                required
                value={password}
                onChange={(ev) => setPassword(ev.target.value)}
              />
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={busy !== null}
                className="flex-1 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
              >
                {busy === 'signin' ? 'Signing in...' : 'Sign in'}
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => void signUpEmail()}
                className="flex-1 rounded-lg border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-secondary-foreground transition-colors hover:bg-border disabled:opacity-50"
              >
                {busy === 'signup' ? 'Creating...' : 'Sign up'}
              </button>
            </div>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
            </div>
          </div>

          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void signInGoogle()}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-secondary-foreground transition-colors hover:bg-border disabled:opacity-50"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            {busy === 'google' ? 'Redirecting...' : 'Google'}
          </button>

          {message && (
            <div className="mt-4 rounded-lg border border-border bg-secondary p-3 text-sm text-muted-foreground">
              {message}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
