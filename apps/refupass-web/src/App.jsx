import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import LoginPage from "./pages/LoginPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import BeneficiaryDetailPage from "./pages/BeneficiaryDetailPage";
import WorkerPage from "./pages/WorkerPage";
import PrintablePassPage from "./pages/PrintablePassPage";

const STORAGE_KEY = "refupass-session";

function loadStoredSession() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
  } catch (_error) {
    return null;
  }
}

function ProtectedRoute({ session }) {
  const location = useLocation();
  if (!session) {
    return <Navigate to="/" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

export default function App() {
  const [session, setSession] = useState(() => loadStoredSession());

  useEffect(() => {
    if (session) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, [session]);

  const onLogin = (nextSession) => {
    setSession(nextSession);
  };

  const onLogout = () => {
    setSession(null);
  };

  const defaultPath = session?.role === "aid_worker" ? "/worker" : "/admin";

  return (
    <Routes>
      <Route
        path="/"
        element={session ? <Navigate to={defaultPath} replace /> : <LoginPage onLogin={onLogin} />}
      />
      <Route element={<ProtectedRoute session={session} />}>
        <Route
          path="/admin"
          element={<AdminDashboardPage session={session} onLogout={onLogout} />}
        />
        <Route
          path="/admin/beneficiaries/:id"
          element={<BeneficiaryDetailPage session={session} onLogout={onLogout} />}
        />
        <Route
          path="/admin/beneficiaries/:id/print"
          element={<PrintablePassPage session={session} onLogout={onLogout} />}
        />
        <Route
          path="/worker"
          element={<WorkerPage session={session} onLogout={onLogout} />}
        />
      </Route>
      <Route path="*" element={<Navigate to={session ? defaultPath : "/"} replace />} />
    </Routes>
  );
}
