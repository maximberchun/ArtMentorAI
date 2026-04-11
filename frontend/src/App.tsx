import { useEffect, useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { apiJson } from './lib/api'
import { supabase } from './lib/supabase'

type AuthMe = {
  user_id: string
  email: string | null
  role: string
}

function Home() {
  const [sessionEmail, setSessionEmail] = useState<string | null>(null)
  const [me, setMe] = useState<AuthMe | null>(null)
  const [meError, setMeError] = useState<string | null>(null)
  const [configOk, setConfigOk] = useState(false)

  useEffect(() => {
    const url = import.meta.env.VITE_SUPABASE_URL
    const key = import.meta.env.VITE_SUPABASE_ANON_KEY
    const api = import.meta.env.VITE_API_BASE_URL
    setConfigOk(Boolean(url && key && api))
  }, [])

  useEffect(() => {
    if (!supabase) return
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSessionEmail(session?.user.email ?? null)
    })
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSessionEmail(session?.user.email ?? null)
    })
    return () => subscription.unsubscribe()
  }, [])

  async function callAuthMe() {
    setMeError(null)
    setMe(null)
    try {
      const data = await apiJson<AuthMe>('/auth/me')
      setMe(data)
    } catch (e) {
      setMeError(e instanceof Error ? e.message : 'Request failed')
    }
  }

  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <h1 className="text-lg font-semibold tracking-tight">ArtMentorAI</h1>
          <nav className="flex gap-4 text-sm text-stone-600">
            <Link className="hover:text-stone-900" to="/">
              Home
            </Link>
            <Link className="hover:text-stone-900" to="/sign-in">
              Sign in
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-sm text-stone-600">
          Vite + React + TypeScript + Tailwind. Supabase client and API helper with bearer token are
          wired in <code className="rounded bg-stone-200 px-1">src/lib/</code>.
        </p>
        {!configOk && (
          <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Set <code className="font-mono">VITE_SUPABASE_URL</code>,{' '}
            <code className="font-mono">VITE_SUPABASE_ANON_KEY</code>, and{' '}
            <code className="font-mono">VITE_API_BASE_URL</code> in <code className="font-mono">.env</code>{' '}
            at the <strong>repo root</strong> or in <code className="font-mono">frontend/</code>, then restart{' '}
            <code className="font-mono">npm run dev</code>. Missing Supabase env previously caused a blank page
            (SDK throws before React mounts).
          </p>
        )}
        <div className="mt-6 rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-sm font-medium text-stone-800">Session</p>
          <p className="mt-1 text-sm text-stone-600">
            {sessionEmail ? `Signed in as ${sessionEmail}` : 'Not signed in'}
          </p>
          <button
            type="button"
            className="mt-3 rounded-md bg-stone-800 px-3 py-1.5 text-sm text-white hover:bg-stone-700 disabled:opacity-50"
            onClick={() => void callAuthMe()}
            disabled={!configOk}
          >
            GET /auth/me (uses bearer token)
          </button>
          {meError && (
            <p className="mt-2 text-sm text-red-700" role="alert">
              {meError}
            </p>
          )}
          {me && (
            <pre className="mt-2 overflow-x-auto rounded bg-stone-50 p-2 text-xs text-stone-800">
              {JSON.stringify(me, null, 2)}
            </pre>
          )}
        </div>
      </main>
    </div>
  )
}

function SignIn() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState<string | null>(null)

  async function signInEmail(e: React.FormEvent) {
    e.preventDefault()
    setMessage(null)
    if (!supabase) {
      setMessage(
        'Supabase env missing. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY, then restart the dev server.',
      )
      return
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    setMessage(error?.message ?? 'Signed in.')
  }

  async function signUpEmail() {
    setMessage(null)
    if (!supabase) {
      setMessage(
        'Supabase env missing. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY, then restart the dev server.',
      )
      return
    }
    const { error } = await supabase.auth.signUp({ email, password })
    setMessage(error?.message ?? 'Check your email to confirm, if required.')
  }

  async function signInGoogle() {
    setMessage(null)
    if (!supabase) {
      setMessage(
        'Supabase env missing. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY, then restart the dev server.',
      )
      return
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
    if (error) {
      setMessage(error.message)
    }
  }

  return (
    <div className="min-h-screen bg-stone-100 px-4 py-10 text-stone-900">
      <div className="mx-auto max-w-md rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold">Sign in</h1>
        <p className="mt-1 text-sm text-stone-600">
          Uses <code className="rounded bg-stone-100 px-1">@supabase/supabase-js</code> with env from{' '}
          <code className="rounded bg-stone-100 px-1">.env</code>.
        </p>
        <form className="mt-4 space-y-3" onSubmit={signInEmail}>
          <label className="block text-sm font-medium text-stone-700">
            Email
            <input
              type="email"
              autoComplete="email"
              className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              required
            />
          </label>
          <label className="block text-sm font-medium text-stone-700">
            Password
            <input
              type="password"
              autoComplete="current-password"
              className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              required
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              className="rounded-md bg-stone-800 px-3 py-2 text-sm text-white hover:bg-stone-700"
            >
              Sign in
            </button>
            <button
              type="button"
              className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm hover:bg-stone-50"
              onClick={() => void signUpEmail()}
            >
              Sign up
            </button>
          </div>
        </form>
        <div className="my-4 border-t border-stone-200 pt-4">
          <button
            type="button"
            className="w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm hover:bg-stone-50"
            onClick={() => void signInGoogle()}
          >
            Continue with Google
          </button>
        </div>
        {message && <p className="text-sm text-stone-700">{message}</p>}
        <p className="mt-4 text-center text-sm">
          <Link className="text-stone-600 underline hover:text-stone-900" to="/">
            Back home
          </Link>
        </p>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/sign-in" element={<SignIn />} />
    </Routes>
  )
}
