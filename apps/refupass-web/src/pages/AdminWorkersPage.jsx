import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { UserPlus, Users2, ArrowLeft } from "lucide-react";
import Shell from "../components/Shell";
import Button from "../components/Button";
import { api } from "../api/client";
import { useToast } from "../components/ToastProvider";

const navItems = [
  { to: "/admin", label: "Overview", end: true, icon: Users2 },
  { to: "/admin/workers", label: "Aid Workers", end: true, icon: UserPlus },
];

const defaultWorkerForm = {
  displayName: "",
  username: "",
  password: "",
  role: "aid_worker",
};

export default function AdminWorkersPage({ session, onLogout }) {
  const ngoName = session.ngoName || "RefuProof NGO";
  const [aidWorkers, setAidWorkers] = useState([]);
  const [workerForm, setWorkerForm] = useState(defaultWorkerForm);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [workerLoading, setWorkerLoading] = useState(false);
  const { showToast } = useToast();

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const workerList = await api.getAidWorkers(session.accessToken);
        setAidWorkers(workerList);
      } catch (error) {
        setStatus(error.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [session.accessToken]);

  const handleWorkerChange = (event) => {
    const { name, value } = event.target;
    setWorkerForm((current) => ({ ...current, [name]: value }));
  };

  const handleWorkerSubmit = async (event) => {
    event.preventDefault();
    setWorkerLoading(true);
    setStatus("");
    try {
      const created = await api.createAidWorker(session.accessToken, workerForm);
      setAidWorkers((current) => [...current, created].sort((a, b) => a.displayName.localeCompare(b.displayName)));
      setWorkerForm(defaultWorkerForm);
      setStatus(`Aid worker ${created.displayName} added to ${created.ngoName}.`);
      showToast({
        title: "Aid worker registered",
        message: `${created.displayName} can now sign in to the field console.`,
        tone: "success",
      });
    } catch (error) {
      setStatus(error.message);
      showToast({
        title: "Could not register aid worker",
        message: error.message,
        tone: "error",
      });
    } finally {
      setWorkerLoading(false);
    }
  };

  const statusTone = status.includes("added") ? "success" : "error";

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Aid Workers"
      subtitle="Register and manage field staff for your NGO."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/admin"><ArrowLeft size={16} strokeWidth={1.5} /> Back</Button>}
    >
      {status ? <div className={`status-banner ${statusTone}`}>{status}</div> : null}

      <div className="split-grid">
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Organization</p>
              <h3>Register aid worker</h3>
            </div>
            <div className="header-chip">
              <span>NGO</span>
              <strong>{ngoName}</strong>
            </div>
          </div>
          <form className="stacked-form" onSubmit={handleWorkerSubmit}>
            <label>
              Worker name
              <input name="displayName" value={workerForm.displayName} onChange={handleWorkerChange} required />
            </label>
            <div className="detail-grid">
              <label>
                Username
                <input name="username" value={workerForm.username} onChange={handleWorkerChange} required />
              </label>
              <label>
                Account type
                <input value="Aid worker" readOnly />
              </label>
              <label>
                Password
                <input type="password" name="password" value={workerForm.password} onChange={handleWorkerChange} required />
              </label>
            </div>
            <div className="card-actions">
              <Button type="submit" disabled={workerLoading}>
                {workerLoading ? "Adding..." : "Register aid worker"}
              </Button>
            </div>
          </form>
        </section>

        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Current staff</p>
              <h3>Worker directory</h3>
            </div>
          </div>
          <div className="simple-list">
            {loading ? (
              <div className="simple-list-row"><strong>Loading...</strong></div>
            ) : aidWorkers.length ? (
              aidWorkers.map((worker) => (
                <div key={worker.id} className="simple-list-row">
                  <strong>{worker.displayName}</strong>
                  <span>{worker.username}</span>
                  <span>{worker.ngoName}</span>
                </div>
              ))
            ) : (
              <div className="simple-list-row"><strong>No workers registered yet</strong></div>
            )}
          </div>
        </section>
      </div>
    </Shell>
  );
}
