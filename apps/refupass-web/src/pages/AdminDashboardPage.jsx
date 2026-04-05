import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Clock3, PackageCheck, UserPlus, Users2, ArrowRight } from "lucide-react";
import Shell from "../components/Shell";
import StatCard from "../components/StatCard";
import { api } from "../api/client";

const navItems = [
  { to: "/admin", label: "Overview", end: true, icon: Users2 },
  { to: "/admin/roster", label: "Roster", end: true, icon: Users2 },
  { to: "/admin/workers", label: "Aid Workers", end: true, icon: UserPlus },
  { to: "/admin/deliveries", label: "Deliveries", end: true, icon: PackageCheck },
];

export default function AdminDashboardPage({ session, onLogout }) {
  const [enrollments, setEnrollments] = useState([]);
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [list, grievanceList] = await Promise.all([
          api.getProgramEnrollments(session.accessToken),
          api.getGrievances(session.accessToken),
        ]);
        setEnrollments(list);
        setGrievances(grievanceList);
      } catch (_error) {
        /* silently handled */
      } finally {
        setLoading(false);
      }
    })();
  }, [session.accessToken]);

  const peopleCount = new Set(enrollments.map((e) => e.person.id)).size;
  const eligibleCount = enrollments.filter((e) => e.currentEligibility?.status === "eligible").length;
  const redeemedCount = enrollments.filter((e) => e.currentRedemption).length;

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="NGO Admin"
      subtitle="Manage enrollments, aid workers, and delivery operations."
      navItems={navItems}
    >
      <div className="stats-grid">
        <StatCard label="Eligible" value={eligibleCount} icon={Users2} />
        <StatCard label="Redeemed" value={redeemedCount} icon={PackageCheck} />
        <StatCard label="Grievances" value={grievances.length} icon={AlertTriangle} />
        <StatCard
          label="Enrollments"
          value={enrollments.length}
          hint={loading ? "Loading" : `${peopleCount} shared people`}
          icon={Clock3}
        />
      </div>

      <div className="hub-card-grid">
        <Link to="/admin/roster" className="hub-card">
          <div className="hub-card-icon"><Users2 size={32} strokeWidth={1.2} /></div>
          <div className="hub-card-body">
            <h3>Enrollment Roster</h3>
            <p>Browse beneficiary enrollments, search, and issue passes.</p>
          </div>
          <ArrowRight size={20} strokeWidth={1.5} className="hub-card-arrow" />
        </Link>

        <Link to="/admin/enrollments/new" className="hub-card">
          <div className="hub-card-icon"><UserPlus size={32} strokeWidth={1.2} /></div>
          <div className="hub-card-body">
            <h3>Enroll Person</h3>
            <p>Search the shared registry and attach a person to your NGO program.</p>
          </div>
          <ArrowRight size={20} strokeWidth={1.5} className="hub-card-arrow" />
        </Link>

        <Link to="/admin/workers" className="hub-card">
          <div className="hub-card-icon"><UserPlus size={32} strokeWidth={1.2} /></div>
          <div className="hub-card-body">
            <h3>Aid Workers</h3>
            <p>Register and manage field staff for your NGO.</p>
          </div>
          <ArrowRight size={20} strokeWidth={1.5} className="hub-card-arrow" />
        </Link>

        <Link to="/admin/deliveries" className="hub-card">
          <div className="hub-card-icon"><PackageCheck size={32} strokeWidth={1.2} /></div>
          <div className="hub-card-body">
            <h3>Deliveries & Grievances</h3>
            <p>Track completed redemptions and follow up on open issues.</p>
          </div>
          <ArrowRight size={20} strokeWidth={1.5} className="hub-card-arrow" />
        </Link>
      </div>
    </Shell>
  );
}
