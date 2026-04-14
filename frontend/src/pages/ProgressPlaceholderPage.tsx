export function ProgressPlaceholderPage() {
  return (
    <section className="rounded border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 shadow-sm">
      <h2 className="text-lg font-semibold">Progress dashboard (placeholder)</h2>
      <p className="mt-2">
        The progress API is not shipped yet. This area is reserved for XP, level, streak, badges, and
        progress history once `GET /progress/me` is available.
      </p>
    </section>
  )
}
