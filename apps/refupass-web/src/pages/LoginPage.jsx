import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ClipboardCheck, Fingerprint, ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import Button from "../components/Button";
import Badge from "../components/Badge";

const staffAccounts = [
  { label: "NGO Admin", username: "admin", password: "admin123", role: "admin" },
  { label: "Aid Worker", username: "aidworker", password: "worker123", role: "aid_worker" },
];

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleQuickFill = (account) => {
    setForm({ username: account.username, password: account.password });
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.login(form);
      onLogin(response);
      navigate(response.role === "aid_worker" ? "/worker" : "/admin", { replace: true });
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
          <Badge tone="neutral" className="hero-badge">Food aid operations</Badge>
          <h1>RefuPass</h1>
          <p>Verify identity, issue entitlements, and record delivery.</p>
          <div className="hero-summary-list">
            <div className="hero-summary-row">
              <span><Fingerprint size={15} strokeWidth={2.3} /></span>
              <strong>Identity</strong>
              <small>eSignet</small>
            </div>
            <div className="hero-summary-row">
              <span><ShieldCheck size={15} strokeWidth={2.3} /></span>
              <strong>Credential</strong>
              <small>Inji</small>
            </div>
            <div className="hero-summary-row">
              <span><ClipboardCheck size={15} strokeWidth={2.3} /></span>
              <strong>Delivery</strong>
              <small>RefuPass</small>
            </div>
          </div>
        </div>
      </section>

      <section className="login-panel">
        <form className="panel-card auth-card" onSubmit={handleSubmit}>
          <p className="eyebrow">Staff access</p>
          <h2>Sign in to RefuPass</h2>
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
          <div className="staff-account-list">
            {staffAccounts.map((account) => (
              <Button
                key={account.role}
                variant="secondary"
                type="button"
                onClick={() => handleQuickFill(account)}
              >
                {account.label}
              </Button>
            ))}
          </div>
        </form>
      </section>
    </div>
  );
}
