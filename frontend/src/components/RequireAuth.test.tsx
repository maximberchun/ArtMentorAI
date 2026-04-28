import { render, screen } from '@testing-library/react'
import type { Session } from '@supabase/supabase-js'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { RequireAuth } from './RequireAuth'

describe('RequireAuth', () => {
  const buildSession = (expiresAt?: number): Session =>
    ({
      access_token: 'token',
      token_type: 'bearer',
      user: { id: 'user-1' },
      expires_at: expiresAt,
    }) as Session

  it('redirects unauthenticated users to sign-in', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={<RequireAuth session={null}>Protected content</RequireAuth>}
          />
          <Route path="/sign-in" element={<div>Sign in page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Sign in page')).toBeInTheDocument()
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
  })

  it('renders children when a session is present', () => {
    render(
      <MemoryRouter>
        <RequireAuth session={buildSession()}>Protected content</RequireAuth>
      </MemoryRouter>,
    )

    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('redirects users when the session is expired', () => {
    const pastTimestamp = Math.floor(Date.now() / 1000) - 60
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={<RequireAuth session={buildSession(pastTimestamp)}>Protected content</RequireAuth>}
          />
          <Route path="/sign-in" element={<div>Sign in page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Sign in page')).toBeInTheDocument()
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
  })
})
