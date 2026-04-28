import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { RequireAuth } from './RequireAuth'

describe('RequireAuth', () => {
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
        <RequireAuth session={{} as never}>Protected content</RequireAuth>
      </MemoryRouter>,
    )

    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })
})
