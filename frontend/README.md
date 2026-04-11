# ArtMentorAI frontend

Vite + React + TypeScript + Tailwind CSS. Auth uses `@supabase/supabase-js` (email/password and Google OAuth). API calls use `src/lib/api.ts`, which attaches `Authorization: Bearer <supabase_access_token>` when a session exists, matching [docs/api-contracts.md](../docs/api-contracts.md).

## Prerequisites

- Node.js 20+ (LTS recommended) and npm

## Environment variables

Create a `.env` with your secrets (never commit it). Vite merges variables from **both** the repository root and `frontend/` (root first, then `frontend/` overrides), so you can keep `VITE_*` next to the Python API or only under `frontend/`.

Start from `frontend/.env.example`:

| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Supabase project URL (Settings → API → Project URL). |
| `VITE_SUPABASE_ANON_KEY` | Supabase **anon** public key (safe in the browser with Row Level Security). |
| `VITE_API_BASE_URL` | FastAPI base URL **without** a trailing slash, e.g. `http://127.0.0.1:8000`. |

Vite inlines only `VITE_*` variables at build time. After changing `.env`, restart the dev server.

### Supabase redirect URLs

For Google OAuth and email magic links, add your app origin under Supabase **Authentication → URL configuration** (e.g. `http://localhost:5173` for local Vite).

### Backend CORS

The API must allow this origin. The Python app defaults include `http://localhost:5173`; override with `ALLOWED_ORIGINS` in the API `.env` if you use another host or port.

## Scripts

```bash
npm install
npm run dev
```

Build and preview:

```bash
npm run build
npm run preview
```

Lint:

```bash
npm run lint
```

## Layout

- `src/lib/supabase.ts` — Supabase client (persisted session, refresh, OAuth callback handling).
- `src/lib/api.ts` — `apiFetch` / `apiJson` helpers for the FastAPI backend.
- `src/App.tsx` — Example routes: home (session + sample `GET /auth/me`) and sign-in.
