import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { clearSession, loadStoredSession, saveSession, subscribeToAuthChanges } from "./api/client";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import PlatformDashboardPage from "./pages/PlatformDashboardPage";
import PlatformNgosPage from "./pages/PlatformNgosPage";
import PlatformPeoplePage from "./pages/PlatformPeoplePage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminRosterPage from "./pages/AdminRosterPage";
import AdminWorkersPage from "./pages/AdminWorkersPage";
import AdminDeliveriesPage from "./pages/AdminDeliveriesPage";
import ProgramEnrollmentDetailPage from "./pages/ProgramEnrollmentDetailPage";
import PersonEnrollmentCreatePage from "./pages/PersonEnrollmentCreatePage";
import WorkerPage from "./pages/WorkerPage";
import PrintablePassPage from "./pages/PrintablePassPage";
import { ToastProvider } from "./components/ToastProvider";

const SUPPORTED_ROLES = new Set(["platform_admin", "ngo_admin", "aid_worker"]);

function ProtectedRoute({ session }) {
  const location = useLocation();
  if (!session) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

function RoleRoute({ session, allowedRoles }) {
  const location = useLocation();
  if (!session) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (!SUPPORTED_ROLES.has(session.role)) {
    return <Navigate to="/login" replace />;
  }
  if (!allowedRoles.includes(session.role)) {
    const fallback =
      session.role === "platform_admin" ? "/platform" : session.role === "aid_worker" ? "/worker" : "/admin";
    return <Navigate to={fallback} replace />;
  }
  return <Outlet />;
}

export default function App() {
  const [session, setSession] = useState(() => {
    const stored = loadStoredSession();
    if (!stored || !SUPPORTED_ROLES.has(stored.role)) {
      return null;
    }
    return stored;
  });

  useEffect(() => {
    if (session) {
      saveSession(session, { emit: false });
    } else {
      clearSession({ emit: false });
    }
  }, [session]);

  useEffect(() => {
    return subscribeToAuthChanges((nextSession) => {
      if (!nextSession || !SUPPORTED_ROLES.has(nextSession.role)) {
        setSession(null);
        return;
      }
      setSession(nextSession);
    });
  }, []);

  const onLogin = (nextSession) => {
    setSession(nextSession);
  };

  const onLogout = () => {
    setSession(null);
  };

  const defaultPath =
    session?.role === "platform_admin"
      ? "/platform"
      : session?.role === "aid_worker"
        ? "/worker"
        : session?.role === "ngo_admin"
          ? "/admin"
          : "/";

  return (
    <ToastProvider>
      <Routes>
        <Route path="/" element={<HomePage session={session} />} />
        <Route
          path="/login"
          element={session ? <Navigate to={defaultPath} replace /> : <LoginPage onLogin={onLogin} />}
        />
        <Route element={<ProtectedRoute session={session} />}>
          {/* Platform Admin */}
          <Route element={<RoleRoute session={session} allowedRoles={["platform_admin"]} />}>
            <Route path="/platform" element={<PlatformDashboardPage session={session} onLogout={onLogout} />} />
            <Route path="/platform/ngos" element={<PlatformNgosPage session={session} onLogout={onLogout} />} />
            <Route path="/platform/people" element={<PlatformPeoplePage session={session} onLogout={onLogout} />} />
          </Route>
          {/* NGO Admin */}
          <Route element={<RoleRoute session={session} allowedRoles={["ngo_admin"]} />}>
            <Route path="/admin" element={<AdminDashboardPage session={session} onLogout={onLogout} />} />
            <Route path="/admin/roster" element={<AdminRosterPage session={session} onLogout={onLogout} />} />
            <Route path="/admin/workers" element={<AdminWorkersPage session={session} onLogout={onLogout} />} />
            <Route path="/admin/deliveries" element={<AdminDeliveriesPage session={session} onLogout={onLogout} />} />
            <Route path="/admin/enrollments/new" element={<PersonEnrollmentCreatePage session={session} onLogout={onLogout} />} />
            <Route path="/admin/enrollments/:id" element={<ProgramEnrollmentDetailPage session={session} onLogout={onLogout} />} />
            <Route path="/admin/enrollments/:id/print" element={<PrintablePassPage session={session} onLogout={onLogout} />} />
          </Route>
          {/* Aid Worker */}
          <Route element={<RoleRoute session={session} allowedRoles={["aid_worker"]} />}>
            <Route path="/worker" element={<WorkerPage session={session} onLogout={onLogout} />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to={session ? defaultPath : "/"} replace />} />
      </Routes>
    </ToastProvider>
  );
}
