import { useState } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { ArrowRight, ShieldCheck, Shield, Users, User } from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/ToastProvider";
import { ROLE_OPTIONS, getRoleLabel } from "../utils/roles";

const ROLE_ICONS = {
  platform_admin: Shield,
  ngo_admin: Users,
  aid_worker: User,
};

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();
  const initialRole = ROLE_OPTIONS.some((option) => option.value === location.state?.preselect)
    ? location.state.preselect
    : "ngo_admin";
  const [form, setForm] = useState({ username: "", password: "", role: initialRole });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    setError("");
  };

  const handleRoleChange = (role) => {
    setForm((current) => ({ ...current, role }));
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.login(form);
      onLogin(response);
      showToast({
        title: `${response.roleLabel} access granted`,
        message: `Signed in as ${response.displayName}.`,
        tone: "success",
      });
      navigate(
        response.role === "platform_admin" ? "/platform" : response.role === "aid_worker" ? "/worker" : "/admin",
        { replace: true },
      );
    } catch (nextError) {
      setError(nextError.message);
      showToast({
        title: `Could not sign in as ${getRoleLabel(form.role)}`,
        message: nextError.message,
        tone: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const selectedRole = ROLE_OPTIONS.find((option) => option.value === form.role) || ROLE_OPTIONS[0];

  return (
    <div className="login-layout">
      <section className="login-hero">
        <div className="login-hero__overlay"></div>
        <div className="login-hero__content">
          <Link to="/" className="login-hero__brand">
            <img src="/refupass-mark.svg" alt="RefuProof" className="login-hero__logo" />
            <span>RefuProof</span>
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
            <p>Choose the workspace you are signing into, then use the matching account.</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="login-role-group" aria-label="Account type">
              {ROLE_OPTIONS.map((option) => {
                const Icon = ROLE_ICONS[option.value];
                const isActive = form.role === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    className={`login-role-option ${isActive ? "active" : ""}`}
                    onClick={() => handleRoleChange(option.value)}
                  >
                    <span className="login-role-option__icon">
                      <Icon size={16} strokeWidth={1.8} />
                    </span>
                    <span className="login-role-option__copy">
                      <strong>{option.label}</strong>
                      <small>{option.description}</small>
                    </span>
                  </button>
                );
              })}
            </div>
            <div className="login-role-banner">
              <span>Signing in as</span>
              <strong>{selectedRole.label}</strong>
            </div>
            <label className="login-field">
              <span>Username</span>
              <input
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder={`${selectedRole.shortLabel.toLowerCase()} username`}
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
