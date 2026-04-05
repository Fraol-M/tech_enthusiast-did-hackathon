import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api } from "../api/client";

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const location = useLocation();
  const preselect = location.state?.preselect || "ngo_admin";
  
  const [mode, setMode] = useState(preselect);
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (location.state?.preselect) {
      setMode(location.state.preselect);
    }
  }, [location.state]);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.login(form);
      onLogin(response);
      navigate(
        response.role === "platform_admin" ? "/platform" : response.role === "aid_worker" ? "/worker" : "/admin",
        { replace: true },
      );
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-layout">
      <section className="login-hero">
        <div className="floating-card">
          <h1>RefuPass</h1>
          <p>Dignity in verification.</p>
        </div>
      </section>

      <section className="login-panel">
        <div className="panel-card auth-card">
          <h2>Secure Access</h2>
          
          <div className="segmented-toggle">
            <button
              type="button"
              className={`segmented-toggle-button ${mode === "platform_admin" ? "active" : ""}`}
              onClick={() => {
                setMode("platform_admin");
                setError("");
              }}
            >
              Platform
            </button>
            <button
              type="button"
              className={`segmented-toggle-button ${mode === "ngo_admin" ? "active" : ""}`}
              onClick={() => {
                setMode("ngo_admin");
                setError("");
              }}
            >
              NGO
            </button>
            <button
              type="button"
              className={`segmented-toggle-button ${mode === "aid_worker" ? "active" : ""}`}
              onClick={() => {
                setMode("aid_worker");
                setError("");
              }}
            >
              Worker
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <label>
              Username
              <input name="username" value={form.username} onChange={handleChange} required />
            </label>
            <label>
              Password
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                required
              />
            </label>
            {error ? <div className="status-banner error">{error}</div> : null}
            <button className="button button-primary full-width" type="submit" disabled={loading} style={{marginTop: '1.5rem'}}>
              {loading ? "Authenticating..." : "Sign In"}
              <ArrowRight size={16} strokeWidth={1.5} />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
