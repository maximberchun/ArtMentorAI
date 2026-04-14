import { FormEvent, useEffect, useState } from 'react'
import { apiJson } from '../lib/api'
import { UserProfile } from '../types/api'
import { splitLines, toMultiline } from '../utils/profileForm'

export function ProfilePage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
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
      setMessage(messageText)
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
      setMessage('Profile saved.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to save profile.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-stone-600">Loading profile...</p>
  }

  return (
    <section className="rounded border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold">Profile</h2>
      <p className="mt-1 text-sm text-stone-600">Line-break separated values for list fields.</p>
      <form className="mt-4 space-y-3" onSubmit={saveProfile}>
        <textarea
          className="min-h-20 w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder="Goals (one per line)"
          value={form.goals}
          onChange={(ev) => setForm((prev) => ({ ...prev, goals: ev.target.value }))}
        />
        <textarea
          className="min-h-20 w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder="Preferred styles (one per line)"
          value={form.preferred_styles}
          onChange={(ev) => setForm((prev) => ({ ...prev, preferred_styles: ev.target.value }))}
        />
        <textarea
          className="min-h-20 w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder="Disliked styles (one per line)"
          value={form.disliked_styles}
          onChange={(ev) => setForm((prev) => ({ ...prev, disliked_styles: ev.target.value }))}
        />
        <textarea
          className="min-h-20 w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder="Favorite artists (one per line)"
          value={form.favorite_artists}
          onChange={(ev) => setForm((prev) => ({ ...prev, favorite_artists: ev.target.value }))}
        />
        <input
          className="w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder="Experience level"
          value={form.experience_level}
          onChange={(ev) => setForm((prev) => ({ ...prev, experience_level: ev.target.value }))}
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.retain_memory}
            onChange={(ev) => setForm((prev) => ({ ...prev, retain_memory: ev.target.checked }))}
          />
          Retain memory for portfolio and critique retrieval
        </label>
        <button
          type="submit"
          disabled={saving}
          className="rounded bg-stone-800 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save profile'}
        </button>
      </form>
      {message && <p className="mt-3 text-sm text-stone-700">{message}</p>}
    </section>
  )
}
