import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PackageCheck, AlertTriangle, ArrowLeft, Users2 } from "lucide-react";
import Shell from "../components/Shell";
import Button from "../components/Button";
import { api } from "../api/client";

const navItems = [
  { to: "/admin", label: "Overview", end: true, icon: Users2 },
  { to: "/admin/deliveries", label: "Deliveries", end: true, icon: PackageCheck },
];

export default function AdminDeliveriesPage({ session, onLogout }) {
  const ngoName = session.ngoName || "RefuProof NGO";
  const [redemptions, setRedemptions] = useState([]);
  const [grievances, setGrievances] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [redemptionList, grievanceList] = await Promise.all([
          api.getRedemptions(session.accessToken),
          api.getGrievances(session.accessToken),
        ]);
        setRedemptions(redemptionList);
        setGrievances(grievanceList);
      } catch (error) {
        setStatus(error.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [session.accessToken]);

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Deliveries & Grievances"
      subtitle="Track completed redemptions and open issues."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/admin"><ArrowLeft size={16} strokeWidth={1.5} /> Back</Button>}
    >
      {status ? <div className="status-banner error">{status}</div> : null}

      <div className="split-grid">
        <section className="panel-card">
          <p className="eyebrow">Redemption log</p>
          <h3>Deliveries</h3>
          <div className="simple-list">
            {loading ? (
              <div className="simple-list-row"><strong>Loading...</strong></div>
            ) : redemptions.length ? (
              redemptions.map((redemption) => (
                <div key={redemption.id} className="simple-list-row">
                  <strong>{redemption.verificationReference}</strong>
                  <span>{ngoName} field team</span>
                  <span>{new Date(redemption.createdAt).toLocaleString()}</span>
                </div>
              ))
            ) : (
              <div className="simple-list-row"><strong>No deliveries recorded yet</strong></div>
            )}
          </div>
        </section>

        <section className="panel-card">
          <p className="eyebrow">Grievances</p>
          <h3>Open issues</h3>
          <div className="simple-list">
            {loading ? (
              <div className="simple-list-row"><strong>Loading...</strong></div>
            ) : grievances.length ? (
              grievances.map((grievance) => (
                <div key={grievance.id} className="simple-list-row">
                  <strong>{grievance.reason}</strong>
                  <span>{ngoName} field team</span>
                  <span>{grievance.status}</span>
                </div>
              ))
            ) : (
              <div className="simple-list-row"><strong>No grievances filed</strong></div>
            )}
          </div>
        </section>
      </div>
    </Shell>
  );
}
