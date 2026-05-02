import { FormEvent, useEffect, useState } from 'react'
import { apiJson } from '../lib/api'
import { UserProfile } from '../types/api'
import { splitLines, toMultiline } from '../utils/profileForm'

export function ProfilePage() {
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <svg className="h-8 w-8 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Profile Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Customize your preferences for personalized critique feedback
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <form className="space-y-6" onSubmit={saveProfile}>
          {/* Goals */}
          <div>
            <label htmlFor="goals" className="mb-1.5 block text-sm font-medium text-foreground">
              Artistic Goals
            </label>
            <textarea
              id="goals"
              className="min-h-24 w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="What do you want to achieve? (one goal per line)"
              value={form.goals}
              onChange={(ev) => setForm((prev) => ({ ...prev, goals: ev.target.value }))}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Enter each goal on a new line
            </p>
          </div>

          {/* Preferred Styles */}
          <div>
            <label htmlFor="preferred_styles" className="mb-1.5 block text-sm font-medium text-foreground">
              Preferred Styles
            </label>
            <textarea
              id="preferred_styles"
              className="min-h-24 w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Art styles you enjoy or want to learn (one per line)"
              value={form.preferred_styles}
              onChange={(ev) => setForm((prev) => ({ ...prev, preferred_styles: ev.target.value }))}
            />
          </div>

          {/* Disliked Styles */}
          <div>
            <label htmlFor="disliked_styles" className="mb-1.5 block text-sm font-medium text-foreground">
              Styles to Avoid
            </label>
            <textarea
              id="disliked_styles"
              className="min-h-24 w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Art styles you want to avoid (one per line)"
              value={form.disliked_styles}
              onChange={(ev) => setForm((prev) => ({ ...prev, disliked_styles: ev.target.value }))}
            />
          </div>

          {/* Favorite Artists */}
          <div>
            <label htmlFor="favorite_artists" className="mb-1.5 block text-sm font-medium text-foreground">
              Favorite Artists
            </label>
            <textarea
              id="favorite_artists"
              className="min-h-24 w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Artists who inspire you (one per line)"
              value={form.favorite_artists}
              onChange={(ev) => setForm((prev) => ({ ...prev, favorite_artists: ev.target.value }))}
            />
          </div>

          {/* Experience Level */}
          <div>
            <label htmlFor="experience_level" className="mb-1.5 block text-sm font-medium text-foreground">
              Experience Level
            </label>
            <select
              id="experience_level"
              className="w-full rounded-lg border border-input bg-background px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              value={form.experience_level}
              onChange={(ev) => setForm((prev) => ({ ...prev, experience_level: ev.target.value }))}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
              <option value="professional">Professional</option>
            </select>
            <p className="mt-1 text-xs text-muted-foreground">
              This helps tailor feedback to your skill level
            </p>
          </div>

          {/* Retain Memory Toggle */}
          <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/50 p-4">
            <div>
              <p className="font-medium text-foreground">Memory Retention</p>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Keep context from previous critiques and portfolio uploads
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={form.retain_memory}
              onClick={() => setForm((prev) => ({ ...prev, retain_memory: !prev.retain_memory }))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                form.retain_memory ? 'bg-primary' : 'bg-muted'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  form.retain_memory ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Saving...
              </span>
            ) : (
              'Save Profile'
            )}
          </button>
        </form>

        {/* Message */}
        {message && (
          <div
            className={`mt-6 rounded-lg border p-4 text-sm ${
              message.type === 'success'
                ? 'border-success/50 bg-success/10 text-success'
                : 'border-destructive/50 bg-destructive/10 text-destructive'
            }`}
          >
            <div className="flex items-center gap-2">
              {message.type === 'success' ? (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              )}
              {message.text}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
