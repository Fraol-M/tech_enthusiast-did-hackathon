import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Building2, ShieldCheck, UserPlus, Users2, ArrowRight } from "lucide-react";
import Shell from "../components/Shell";
import { api } from "../api/client";
import StatCard from "../components/StatCard";

const navItems = [
  { to: "/platform", label: "Overview", end: true, icon: ShieldCheck },
  { to: "/platform/ngos", label: "NGO Registry", end: true, icon: Building2 },
  { to: "/platform/people", label: "People Registry", end: true, icon: Users2 },
];

export default function PlatformDashboardPage({ session, onLogout }) {
  const [ngos, setNgos] = useState([]);
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [ngoPayload, peoplePayload] = await Promise.all([
          api.getPlatformNgos(session.accessToken),
          api.getPeople(session.accessToken),
        ]);
        setNgos(ngoPayload);
        setPeople(peoplePayload);
      } catch (_error) {
        /* silently handled */
      } finally {
        setLoading(false);
      }
    })();
  }, [session.accessToken]);

  const ngoCount = ngos.length;
  const peopleCount = people.length;
  const adminCount = ngos.filter((ngo) => ngo.adminUsername).length;
  const workerCount = ngos.reduce((sum, ngo) => sum + ngo.aidWorkerCount, 0);
  const enrollmentCount = ngos.reduce((sum, ngo) => sum + ngo.enrollmentCount, 0);

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Platform"
      subtitle="Global oversight of NGOs, people, and enrollment activity."
      navItems={navItems}
    >
      <div className="stats-grid">
        <StatCard label="NGOs" value={ngoCount} icon={Building2} />
        <StatCard label="People" value={peopleCount} icon={Users2} />
        <StatCard label="NGO admins" value={adminCount} icon={Users2} />
        <StatCard label="Aid workers" value={workerCount} icon={UserPlus} />
        <StatCard label="Enrollments" value={enrollmentCount} hint={loading ? "Loading" : "Across all NGOs"} icon={ShieldCheck} />
      </div>

      <div className="hub-card-grid">
        <Link to="/platform/ngos" className="hub-card">
          <div className="hub-card-icon"><Building2 size={32} strokeWidth={1.2} /></div>
          <div className="hub-card-body">
            <h3>NGO Registry</h3>
            <p>Register new NGO workspaces and view existing organizations.</p>
          </div>
          <ArrowRight size={20} strokeWidth={1.5} className="hub-card-arrow" />
        </Link>

        <Link to="/platform/people" className="hub-card">
          <div className="hub-card-icon"><Users2 size={32} strokeWidth={1.2} /></div>
          <div className="hub-card-body">
            <h3>People Registry</h3>
            <p>Verify identities through eSignet and manage the shared person registry.</p>
          </div>
          <ArrowRight size={20} strokeWidth={1.5} className="hub-card-arrow" />
        </Link>
      </div>
    </Shell>
  );
}
