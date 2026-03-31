import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api } from "../api/client";
import Button from "../components/Button";
import Badge from "../components/Badge";

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [mode, setMode] = useState("ngo_admin");
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
          <Badge tone="neutral" className="hero-badge">RefuPass</Badge>
          <h1>RefuPass</h1>
          <p>Sign in</p>
        </div>
      </section>

      <section className="login-panel">
        <div className="panel-card auth-card">
          <div className="segmented-toggle">
            <button
              type="button"
              className={`segmented-toggle-button ${mode === "platform_admin" ? "active" : ""}`}
              onClick={() => {
                setMode("platform_admin");
                setError("");
              }}
            >
              Platform admin
            </button>
            <button
              type="button"
              className={`segmented-toggle-button ${mode === "ngo_admin" ? "active" : ""}`}
              onClick={() => {
                setMode("ngo_admin");
                setError("");
              }}
            >
              NGO admin
            </button>
            <button
              type="button"
              className={`segmented-toggle-button ${mode === "aid_worker" ? "active" : ""}`}
              onClick={() => {
                setMode("aid_worker");
                setError("");
              }}
            >
              Aid worker
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <p className="eyebrow">Secure access</p>
            <h2>
              {mode === "platform_admin"
                ? "Platform admin sign in"
                : mode === "ngo_admin"
                  ? "NGO admin sign in"
                  : "Aid worker sign in"}
            </h2>
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
            <Button className="full-width" type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Enter workspace"}
              <ArrowRight size={16} strokeWidth={2.2} />
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}
