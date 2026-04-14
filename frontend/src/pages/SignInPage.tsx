import { FormEvent, useEffect, useRef, useState } from 'react'
import { Session } from '@supabase/supabase-js'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

type SignInPageProps = {
  session: Session | null
}

export function SignInPage({ session }: SignInPageProps) {
  const navigate = useNavigate()
  const formRef = useRef<HTMLFormElement>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState<'signin' | 'signup' | 'google' | null>(null)

  useEffect(() => {
    if (session) {
      void navigate('/', { replace: true })
    }
  }, [navigate, session])

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
    <div className="mx-auto mt-14 max-w-md rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold">Sign in</h2>
      <p className="mt-1 text-sm text-stone-600">Use email/password or Google via Supabase Auth.</p>
      <form ref={formRef} className="mt-4 space-y-3" onSubmit={signInEmail}>
        <label className="block text-sm">
          Email
          <input
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
          />
        </label>
        <label className="block text-sm">
          Password
          <input
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            type="password"
            autoComplete="current-password"
            minLength={6}
            required
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
          />
        </label>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={busy !== null}
            className="rounded bg-stone-800 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            {busy === 'signin' ? 'Signing in...' : 'Sign in'}
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void signUpEmail()}
            className="rounded border border-stone-300 bg-white px-3 py-2 text-sm disabled:opacity-50"
          >
            {busy === 'signup' ? 'Creating...' : 'Sign up'}
          </button>
        </div>
      </form>
      <button
        type="button"
        disabled={busy !== null}
        onClick={() => void signInGoogle()}
        className="mt-4 w-full rounded border border-stone-300 bg-white px-3 py-2 text-sm disabled:opacity-50"
      >
        {busy === 'google' ? 'Redirecting...' : 'Continue with Google'}
      </button>
      {message && <p className="mt-3 text-sm text-stone-700">{message}</p>}
    </div>
  )
}
