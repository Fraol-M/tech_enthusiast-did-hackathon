import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Building2, ArrowLeft } from "lucide-react";
import Shell from "../components/Shell";
import Button from "../components/Button";
import { api } from "../api/client";

const navItems = [
  { to: "/platform", label: "Overview", end: true, icon: Building2 },
  { to: "/platform/ngos", label: "NGO Registry", end: true, icon: Building2 },
];

const defaultForm = {
  ngoName: "",
  adminDisplayName: "",
  username: "",
  password: "",
};

export default function PlatformNgosPage({ session, onLogout }) {
  const [ngos, setNgos] = useState([]);
  const [form, setForm] = useState(defaultForm);
  const [status, setStatus] = useState("");
  const [statusTone, setStatusTone] = useState("success");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const payload = await api.getPlatformNgos(session.accessToken);
        setNgos(payload);
      } catch (error) {
        setStatusTone("error");
        setStatus(error.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [session.accessToken]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setStatusTone("success");
    setStatus("");
    try {
      const created = await api.createPlatformNgo(session.accessToken, form);
      setNgos((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setForm(defaultForm);
      setStatus(`${created.name} registered with NGO admin ${created.adminDisplayName}.`);
    } catch (error) {
      setStatusTone("error");
      setStatus(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="NGO Registry"
      subtitle="Register new NGO workspaces and manage existing organizations."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/platform"><ArrowLeft size={16} strokeWidth={1.5} /> Back</Button>}
    >
      {status ? <div className={`status-banner ${statusTone}`}>{status}</div> : null}

      <div className="split-grid">
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Workspace setup</p>
              <h3>Register NGO</h3>
            </div>
          </div>
          <form className="stacked-form" onSubmit={handleSubmit}>
            <label>
              NGO name
              <input name="ngoName" value={form.ngoName} onChange={handleChange} required />
            </label>
            <label>
              NGO admin name
              <input name="adminDisplayName" value={form.adminDisplayName} onChange={handleChange} required />
            </label>
            <label>
              NGO admin username
              <input name="username" value={form.username} onChange={handleChange} required />
            </label>
            <label>
              Password
              <input type="password" name="password" value={form.password} onChange={handleChange} required />
            </label>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Registering..." : "Create NGO workspace"}
            </Button>
          </form>
        </section>

        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Current workspaces</p>
              <h3>NGO directory</h3>
            </div>
          </div>
          <div className="simple-list">
            {loading ? (
              <div className="simple-list-row"><strong>Loading...</strong></div>
            ) : ngos.length ? (
              ngos.map((ngo) => (
                <div key={ngo.id} className="simple-list-row">
                  <strong>{ngo.name}</strong>
                  <span>{ngo.adminDisplayName || "No NGO admin"}</span>
                  <span>{ngo.adminUsername || "unassigned"}</span>
                  <span>{ngo.enrollmentCount} enrollments</span>
                </div>
              ))
            ) : (
              <div className="simple-list-row"><strong>No NGOs registered yet</strong></div>
            )}
          </div>
        </section>
      </div>
    </Shell>
  );
}
