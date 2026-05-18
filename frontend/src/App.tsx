import { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { RequireAuth } from './components/RequireAuth'
import { useAuthSession } from './hooks/useAuthSession'
import { ConversationPage } from './pages/ConversationPage'
import { CritiquePage } from './pages/CritiquePage'
import { HistoryPage } from './pages/HistoryPage'
import { HomePage } from './pages/HomePage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ProfilePage } from './pages/ProfilePage'
import { ProgressPage } from './pages/ProgressPage'
import { SignInPage } from './pages/SignInPage'

export default function App() {
  const { session, signOut } = useAuthSession()

  function withShell(content: ReactNode) {
    return (
      <AppShell session={session} onSignOut={signOut}>
        {content}
      </AppShell>
    )
  }

  function withAuth(content: ReactNode) {
    return withShell(<RequireAuth session={session}>{content}</RequireAuth>)
  }

  return (
    <Routes>
      <Route path="/sign-in" element={withShell(<SignInPage session={session} />)} />
      <Route path="/" element={withShell(<HomePage />)} />
      <Route path="/critique" element={withShell(<CritiquePage session={session} />)} />
      <Route path="/conversation" element={withShell(<ConversationPage session={session} />)} />
      <Route path="/profile" element={withAuth(<ProfilePage />)} />
      <Route path="/portfolio" element={withAuth(<PortfolioPage />)} />
      <Route path="/history" element={withAuth(<HistoryPage />)} />
      <Route path="/progress" element={withAuth(<ProgressPage />)} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
