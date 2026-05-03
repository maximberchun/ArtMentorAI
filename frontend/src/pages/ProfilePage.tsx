import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react'
import { apiJson } from '../lib/api'
import { useAuthSession } from '../hooks/useAuthSession'
import { UserProfile } from '../types/api'
import { splitLines, toMultiline } from '../utils/profileForm'

const EXPERIENCE_LEVELS = [
  { value: 'beginner', label: 'Beginner', caption: 'Core concepts' },
  { value: 'intermediate', label: 'Intermediate', caption: 'Building consistency' },
  { value: 'advanced', label: 'Advanced', caption: 'Refining craft' },
  { value: 'professional', label: 'Professional', caption: 'Portfolio-ready' },
] as const

const textareaClass =
  'min-h-[7.5rem] w-full resize-y rounded-xl border border-input/80 bg-background/60 px-4 py-3 text-sm text-foreground shadow-[inset_0_1px_0_0_hsl(0_0%_100%_/_.04)] placeholder:text-muted-foreground transition-[border-color,box-shadow] focus:border-primary/60 focus:outline-none focus:ring-2 focus:ring-primary/25'

function FormSection({
  icon,
  title,
  description,
  children,
}: {
  icon: ReactNode
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-border/90 bg-gradient-to-b from-card to-card/95 p-6 shadow-[0_1px_0_0_hsl(0_0%_100%_/_.06)_inset]">
      <div className="pointer-events-none absolute -right-8 -top-12 h-40 w-40 rounded-full bg-primary/[0.07] blur-2xl" />
      <div className="relative">
        <div className="mb-5 flex gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/20">
            {icon}
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold tracking-tight text-foreground">{title}</h2>
            <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
          </div>
        </div>
        {children}
      </div>
    </section>
  )
}

function initialsFromEmail(email: string | undefined) {
  if (!email) return '?'
  const local = email.split('@')[0] ?? ''
  const parts = local.split(/[._-]+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0]![0]! + parts[1]![0]!).toUpperCase()
  }
  return local.slice(0, 2).toUpperCase() || '?'
}

export function ProfilePage() {
  const { session } = useAuthSession()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [form, setForm] = useState({
    goals: '',
    preferred_styles: '',
    disliked_styles: '',
    favorite_artists: '',
    experience_level: 'beginner',
    retain_memory: true,
  })

  const counts = useMemo(
    () => ({
      goals: splitLines(form.goals).length,
      preferred: splitLines(form.preferred_styles).length,
      avoided: splitLines(form.disliked_styles).length,
      artists: splitLines(form.favorite_artists).length,
    }),
    [form.goals, form.preferred_styles, form.disliked_styles, form.favorite_artists],
  )

  async function loadProfile() {
    setLoading(true)
    setMessage(null)
    try {
      const profile = await apiJson<UserProfile>('/profile/me')
      setForm({
        goals: toMultiline(profile.goals),
        preferred_styles: toMultiline(profile.preferred_styles),
        disliked_styles: toMultiline(profile.disliked_styles),
        favorite_artists: toMultiline(profile.favorite_artists),
        experience_level: profile.experience_level || 'beginner',
        retain_memory: profile.retain_memory,
      })
    } catch (err) {
      const messageText = err instanceof Error ? err.message : 'Failed to load profile.'
      setMessage({ type: 'error', text: messageText })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadProfile()
  }, [])

  async function saveProfile(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      await apiJson<UserProfile>('/profile/me', {
        method: 'PUT',
        body: JSON.stringify({
          goals: splitLines(form.goals),
          preferred_styles: splitLines(form.preferred_styles),
          disliked_styles: splitLines(form.disliked_styles),
          favorite_artists: splitLines(form.favorite_artists),
          experience_level: form.experience_level.trim() || 'beginner',
          retain_memory: form.retain_memory,
        }),
      })
      setMessage({ type: 'success', text: 'Profile saved successfully.' })
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to save profile.' })
    } finally {
      setSaving(false)
    }
  }

  const email = session?.user.email
  const initials = initialsFromEmail(email)

  if (loading) {
    return (
      <div className="space-y-8 pb-8">
        <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-card/50 p-8">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,hsl(var(--primary)/0.22),transparent)]" />
          <div className="animate-pulse space-y-4">
            <div className="h-4 w-24 rounded-full bg-muted" />
            <div className="h-9 max-w-md rounded-lg bg-muted" />
            <div className="h-4 max-w-lg rounded bg-muted" />
          </div>
        </div>
        <div className="grid gap-8 lg:grid-cols-12">
          <div className="space-y-4 lg:col-span-4">
            <div className="h-48 animate-pulse rounded-2xl border border-border/60 bg-card/40" />
            <div className="h-36 animate-pulse rounded-2xl border border-border/60 bg-card/40" />
          </div>
          <div className="space-y-4 lg:col-span-8">
            <div className="h-64 animate-pulse rounded-2xl border border-border/60 bg-card/40" />
            <div className="h-64 animate-pulse rounded-2xl border border-border/60 bg-card/40" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8 pb-10">
      <header className="relative overflow-hidden rounded-2xl border border-border/90 bg-card/80 px-6 py-8 sm:px-8">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-0 h-[420px] w-[min(100%,56rem)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/[0.18] blur-3xl" />
          <div className="absolute bottom-0 right-0 h-48 w-48 translate-x-1/4 translate-y-1/4 rounded-full bg-primary/[0.08] blur-2xl" />
        </div>
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl space-y-3">
            <p className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-primary">
              <span className="h-1 w-1 rounded-full bg-primary shadow-[0_0_8px_hsl(var(--primary))]" />
              Personalization
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">Your creative profile</h1>
            <p className="text-base leading-relaxed text-muted-foreground">
              Tell Art Mentor how you like to work so critiques, chat, and practice suggestions stay aligned with your
              taste and goals.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadProfile()}
            disabled={saving}
            className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-xl border border-border bg-secondary/80 px-4 py-2.5 text-sm font-medium text-secondary-foreground shadow-sm transition-colors hover:bg-secondary disabled:opacity-50"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
              />
            </svg>
            Reload from server
          </button>
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
        <aside className="space-y-4 lg:sticky lg:top-24 lg:col-span-4">
          <div className="overflow-hidden rounded-2xl border border-border/90 bg-card p-6">
            <div className="flex items-center gap-4">
              <div
                className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-primary/10 text-lg font-semibold text-primary-foreground ring-2 ring-primary/25"
                aria-hidden
              >
                {initials}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{email ?? 'Signed in'}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">Preferences apply across critique and chat</p>
              </div>
            </div>
            <dl className="mt-6 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl bg-secondary/50 px-3 py-2.5 ring-1 ring-border/60">
                <dt className="text-xs text-muted-foreground">Goals</dt>
                <dd className="mt-0.5 font-semibold tabular-nums text-foreground">{counts.goals}</dd>
              </div>
              <div className="rounded-xl bg-secondary/50 px-3 py-2.5 ring-1 ring-border/60">
                <dt className="text-xs text-muted-foreground">Styles you like</dt>
                <dd className="mt-0.5 font-semibold tabular-nums text-foreground">{counts.preferred}</dd>
              </div>
              <div className="rounded-xl bg-secondary/50 px-3 py-2.5 ring-1 ring-border/60">
                <dt className="text-xs text-muted-foreground">Styles to skip</dt>
                <dd className="mt-0.5 font-semibold tabular-nums text-foreground">{counts.avoided}</dd>
              </div>
              <div className="rounded-xl bg-secondary/50 px-3 py-2.5 ring-1 ring-border/60">
                <dt className="text-xs text-muted-foreground">Artists</dt>
                <dd className="mt-0.5 font-semibold tabular-nums text-foreground">{counts.artists}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-2xl border border-primary/20 bg-primary/[0.06] p-5">
            <p className="text-sm font-medium text-foreground">Tip</p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              One idea per line keeps your profile easy for the model to parse—short phrases beat long paragraphs here.
            </p>
          </div>
        </aside>

        <div className="space-y-6 lg:col-span-8">
          {message && (
            <div
              role="status"
              className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${
                message.type === 'success'
                  ? 'border-success/40 bg-success/10 text-success'
                  : 'border-destructive/40 bg-destructive/10 text-destructive'
              }`}
            >
              {message.type === 'success' ? (
                <svg className="mt-0.5 h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="mt-0.5 h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                  />
                </svg>
              )}
              <span>{message.text}</span>
            </div>
          )}

          <form className="space-y-6" onSubmit={saveProfile}>
            <FormSection
              title="Direction"
              description="What you are trying to achieve right now—goals shape tone and priorities in feedback."
              icon={
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m0-12h2.25m-13.5 0h2.25m0 0V9m0 4.5V9m0 4.5v3.75m0-3.75h6.75m-6.75 0h6.75m0 0V16.5m0-3.75V9"
                  />
                </svg>
              }
            >
              <div>
                <label htmlFor="goals" className="mb-2 block text-sm font-medium text-foreground">
                  Artistic goals
                </label>
                <textarea
                  id="goals"
                  className={textareaClass}
                  placeholder="e.g. Stronger figure drawing&#10;More confident color choices"
                  value={form.goals}
                  onChange={(ev) => setForm((prev) => ({ ...prev, goals: ev.target.value }))}
                />
                <p className="mt-2 text-xs text-muted-foreground">Enter each goal on its own line.</p>
              </div>
            </FormSection>

            <FormSection
              title="Taste map"
              description="Help the mentor lean into styles you love and steer away from what does not fit."
              icon={
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.431-.198-.812-.42-1.065l-1.09-1.09a3 3 0 00-3.731-.067 3 3 0 00-.415 1.06v.004zM15.75 9.75a3 3 0 118.25 4.5 3 3 0 01-8.25-4.5z"
                  />
                </svg>
              }
            >
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <label htmlFor="preferred_styles" className="mb-2 block text-sm font-medium text-foreground">
                    Preferred styles
                  </label>
                  <textarea
                    id="preferred_styles"
                    className={textareaClass}
                    placeholder="Impressionist brushwork, graphic novels…"
                    value={form.preferred_styles}
                    onChange={(ev) => setForm((prev) => ({ ...prev, preferred_styles: ev.target.value }))}
                  />
                </div>
                <div>
                  <label htmlFor="disliked_styles" className="mb-2 block text-sm font-medium text-foreground">
                    Styles to avoid
                  </label>
                  <textarea
                    id="disliked_styles"
                    className={textareaClass}
                    placeholder="Hyperrealism, heavy airbrush…"
                    value={form.disliked_styles}
                    onChange={(ev) => setForm((prev) => ({ ...prev, disliked_styles: ev.target.value }))}
                  />
                </div>
              </div>
            </FormSection>

            <FormSection
              title="North stars"
              description="Reference artists give concrete anchors for vocabulary and composition in critiques."
              icon={
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                  />
                </svg>
              }
            >
              <div>
                <label htmlFor="favorite_artists" className="mb-2 block text-sm font-medium text-foreground">
                  Favorite artists
                </label>
                <textarea
                  id="favorite_artists"
                  className={textareaClass}
                  placeholder="One artist or studio per line"
                  value={form.favorite_artists}
                  onChange={(ev) => setForm((prev) => ({ ...prev, favorite_artists: ev.target.value }))}
                />
              </div>
            </FormSection>

            <FormSection
              title="Level & memory"
              description="Calibrate explanation depth and whether past sessions should inform new ones."
              icon={
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M10.5 6h9.75M10.5 6a1.5 1.5 0 01-1.5-1.5h-9a1.5 1.5 0 000 3h6.75M10.5 6a1.5 1.5 0 011.5 1.5m-9 3.75h9.75m-9.75 0a1.5 1.5 0 00-1.5 1.5v9.75a1.5 1.5 0 001.5 1.5h9.75a1.5 1.5 0 001.5-1.5v-9.75a1.5 1.5 0 00-1.5-1.5m-12 0V9.75A1.5 1.5 0 013.75 9h6.75"
                  />
                </svg>
              }
            >
              <div className="space-y-6">
                <div>
                  <p id="experience_level_label" className="mb-3 text-sm font-medium text-foreground">
                    Experience level
                  </p>
                  <div
                    role="radiogroup"
                    aria-labelledby="experience_level_label"
                    className="grid gap-2 sm:grid-cols-2"
                  >
                    {EXPERIENCE_LEVELS.map((level) => {
                      const selected = form.experience_level === level.value
                      return (
                        <button
                          key={level.value}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          onClick={() => setForm((prev) => ({ ...prev, experience_level: level.value }))}
                          className={`flex flex-col rounded-xl border px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
                            selected
                              ? 'border-primary/50 bg-primary/10 ring-1 ring-primary/30'
                              : 'border-border/80 bg-background/40 hover:border-border hover:bg-secondary/40'
                          }`}
                        >
                          <span className="text-sm font-medium text-foreground">{level.label}</span>
                          <span className="mt-0.5 text-xs text-muted-foreground">{level.caption}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="flex flex-col gap-4 rounded-2xl border border-border/80 bg-secondary/30 p-5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">Memory retention</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Keep context from previous critiques and portfolio uploads.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={form.retain_memory}
                    aria-label={form.retain_memory ? 'Memory retention enabled' : 'Memory retention disabled'}
                    onClick={() => setForm((prev) => ({ ...prev, retain_memory: !prev.retain_memory }))}
                    className={`relative inline-flex h-8 w-14 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
                      form.retain_memory ? 'bg-primary' : 'bg-muted'
                    }`}
                  >
                    <span
                      className={`inline-block h-6 w-6 transform rounded-full bg-white shadow-sm transition-transform ${
                        form.retain_memory ? 'translate-x-7' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </FormSection>

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-colors hover:bg-primary/90 disabled:opacity-50 sm:w-auto sm:min-w-[11rem]"
              >
                {saving ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Saving…
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                    Save profile
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
