import { createBrowserRouter, RouterProvider, Outlet, Navigate, useLocation } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import SetupPage from './pages/SetupPage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import SearchPage from './pages/SearchPage'
import CatalogPage from './pages/CatalogPage'
import ToolkitsPage from './pages/ToolkitsPage'
import ToolkitDetailPage from './pages/ToolkitDetailPage'
import CredentialsPage from './pages/CredentialsPage'
import OAuthBrokersPage from './pages/OAuthBrokersPage'
import CredentialFormPage from './pages/CredentialFormPage'
import WorkflowsPage from './pages/WorkflowsPage'
import WorkflowDetailPage from './pages/WorkflowDetailPage'
import TracesPage from './pages/TracesPage'
import JobsPage from './pages/JobsPage'
import JobDetailPage from './pages/JobDetailPage'
import TraceDetailPage from './pages/TraceDetailPage'
import ApprovalPage from './pages/ApprovalPage'
import { useAuth } from './hooks/useAuth'

function AuthGuard() {
  const { user, isLoading, isAccountRequired } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  if (isAccountRequired) {
    if (location.pathname !== '/setup') return <Navigate to="/setup" replace />
    return <Outlet />
  }

  if (!user?.logged_in) {
    if (location.pathname !== '/login') {
      return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
    }
    return <Outlet />
  }

  if (location.pathname === '/login' || location.pathname === '/setup') {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}

const router = createBrowserRouter([
  {
    element: <AuthGuard />,
    children: [
      { path: '/setup', element: <SetupPage /> },
      { path: '/login', element: <LoginPage /> },
      // Approval page has minimal chrome — outside Layout
      { path: '/approve/:toolkit_id/:req_id', element: <ApprovalPage /> },
      {
        element: <Layout />,
        children: [
          { path: '/', element: <DashboardPage /> },
          { path: '/search', element: <SearchPage /> },
          { path: '/catalog', element: <CatalogPage /> },
          { path: '/workflows', element: <WorkflowsPage /> },
          { path: '/workflows/:slug', element: <WorkflowDetailPage /> },
          { path: '/toolkits', element: <ToolkitsPage /> },
          { path: '/toolkits/new', element: <ToolkitsPage createNew /> },
          { path: '/toolkits/:id', element: <ToolkitDetailPage /> },
          { path: '/credentials', element: <CredentialsPage /> },
          { path: '/credentials/new', element: <CredentialFormPage /> },
          { path: '/credentials/:id/edit', element: <CredentialFormPage /> },
          { path: '/oauth-brokers', element: <OAuthBrokersPage /> },
          { path: '/traces', element: <TracesPage /> },
          { path: '/traces/:id', element: <TraceDetailPage /> },
          { path: '/jobs', element: <JobsPage /> },
          { path: '/jobs/:id', element: <JobDetailPage /> },
        ]
      }
    ]
  }
])

export default function App() {
  return <RouterProvider router={router} />
}
