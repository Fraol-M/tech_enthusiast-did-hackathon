import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { api } from "../api/client";

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
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
        <div className="login-hero__overlay"></div>
        <div className="login-hero__content">
          <Link to="/" className="login-hero__brand">
            <img src="/refupass-mark.svg" alt="RefuPass" className="login-hero__logo" />
            <span>RefuPass</span>
          </Link>
          <div className="login-hero__tagline">
            <h1>Dignity in<br/>Verification.</h1>
            <p>Secure, verifiable aid distribution for the world's most vulnerable communities.</p>
          </div>
          <p className="login-hero__built">Built for everyone — Aid Workers, NGO Administrators, and Platform Teams.</p>
        </div>
      </section>

      <section className="login-panel">
        <div className="login-panel__inner">
          <div className="login-panel__header">
            <div className="login-panel__icon-wrap">
              <ShieldCheck size={24} strokeWidth={1.5} />
            </div>
            <h2>Secure Access</h2>
            <p>Sign in with your assigned RefuPass account</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <label className="login-field">
              <span>Username</span>
              <input
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder="Enter your username"
                required
              />
            </label>
            <label className="login-field">
              <span>Password</span>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="Enter your password"
                required
              />
            </label>
            {error ? <div className="status-banner error">{error}</div> : null}
            <button className="button button-primary full-width login-submit" type="submit" disabled={loading}>
              {loading ? "Authenticating..." : "Sign In"}
              <ArrowRight size={16} strokeWidth={1.5} />
            </button>
          </form>

          <div className="login-panel__footer">
            <Link to="/" className="login-back-link">
              <ArrowRight size={14} strokeWidth={1.5} style={{transform: 'rotate(180deg)'}} />
              Back to homepage
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
