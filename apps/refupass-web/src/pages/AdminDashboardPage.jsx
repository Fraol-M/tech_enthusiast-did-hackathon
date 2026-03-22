import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, Clock3, PackageCheck, Search, Users2 } from "lucide-react";
import Shell from "../components/Shell";
import StatCard from "../components/StatCard";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";

const navItems = [{ to: "/admin", label: "Admin dashboard", end: true, icon: Users2 }];

export default function AdminDashboardPage({ session, onLogout }) {
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [currentCycle, setCurrentCycle] = useState(null);
  const [redemptions, setRedemptions] = useState([]);
  const [grievances, setGrievances] = useState([]);
  const [search, setSearch] = useState("");
  const [issuanceSession, setIssuanceSession] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      try {
        const [cycle, list, redemptionList, grievanceList] = await Promise.all([
          api.getCurrentCycle(session.accessToken),
          api.getBeneficiaries(session.accessToken),
          api.getRedemptions(session.accessToken),
          api.getGrievances(session.accessToken),
        ]);
        setCurrentCycle(cycle);
        setBeneficiaries(list);
        setRedemptions(redemptionList);
        setGrievances(grievanceList);
      } catch (error) {
        setStatus(error.message);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [session.accessToken]);

  const filteredBeneficiaries = useMemo(() => {
    if (!search.trim()) {
      return beneficiaries;
    }
    const needle = search.toLowerCase();
    return beneficiaries.filter((beneficiary) =>
      [beneficiary.fullName, beneficiary.authSubject, beneficiary.beneficiaryCode]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(needle)),
    );
  }, [beneficiaries, search]);

  const eligibleCount = beneficiaries.filter(
    (beneficiary) => beneficiary.currentEligibility?.status === "eligible",
  ).length;
  const redeemedCount = beneficiaries.filter((beneficiary) => beneficiary.currentRedemption).length;

  const handleIssue = async (beneficiaryId) => {
    setStatus("");
    try {
      const sessionPayload = await api.createIssuanceSession(session.accessToken, beneficiaryId);
      setIssuanceSession(sessionPayload);
    } catch (error) {
      setStatus(error.message);
    }
  };

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Admin"
      subtitle="Eligibility, issuance, and delivery."
      navItems={navItems}
      aside={
        currentCycle ? (
          <div className="header-chip">
            <span>Current cycle</span>
            <strong>{currentCycle.name}</strong>
          </div>
        ) : null
      }
    >
      {status ? <div className="status-banner error">{status}</div> : null}

      <div className="stats-grid">
        <StatCard label="Eligible" value={eligibleCount} icon={Users2} />
        <StatCard label="Redeemed" value={redeemedCount} icon={PackageCheck} />
        <StatCard label="Grievances" value={grievances.length} icon={AlertTriangle} />
        <StatCard
          label="Beneficiaries"
          value={beneficiaries.length}
          hint={loading ? "Loading" : undefined}
          icon={Clock3}
        />
      </div>

      {issuanceSession ? (
        <section className="panel-card session-panel">
          <div className="session-panel-copy">
            <p className="eyebrow">Latest issuance</p>
            <h3>{issuanceSession.credentialPreview.fullName}</h3>
          </div>
          <div className="issuance-actions">
            <Button as="a" href={issuanceSession.launchUrl} target="_blank" rel="noreferrer">
              Open Inji Web
              <ArrowUpRight size={16} strokeWidth={2.2} />
            </Button>
            <p className="code-chip">{issuanceSession.credentialConfigurationId}</p>
          </div>
          <div className="detail-grid">
            <div>
              <span>Beneficiary</span>
              <strong>{issuanceSession.credentialPreview.beneficiaryId}</strong>
            </div>
            <div>
              <span>Household</span>
              <strong>{issuanceSession.credentialPreview.householdId}</strong>
            </div>
            <div>
              <span>Cycle</span>
              <strong>{issuanceSession.credentialPreview.aidCycle}</strong>
            </div>
            <div>
              <span>Ration tier</span>
              <strong>{issuanceSession.credentialPreview.rationTier}</strong>
            </div>
          </div>
        </section>
      ) : null}

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Beneficiaries</p>
            <h3>Records</h3>
          </div>
          <div className="search-wrap">
            <Search size={16} strokeWidth={2.2} />
            <input
              className="search-input"
              placeholder="Search by name, auth subject, or beneficiary code"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>
        <div className="beneficiary-grid">
          {filteredBeneficiaries.map((beneficiary) => (
            <article key={beneficiary.id} className="beneficiary-card">
              <div className="card-header-row">
                <div>
                  <h4>{beneficiary.fullName}</h4>
                  <p>{beneficiary.beneficiaryCode}</p>
                </div>
                <Badge tone={beneficiary.currentEligibility?.status || "pending"}>
                  {beneficiary.currentEligibility?.status || "pending"}
                </Badge>
              </div>
              <dl className="card-facts">
                <div>
                  <dt>Auth subject</dt>
                  <dd>{beneficiary.authSubject}</dd>
                </div>
                <div>
                  <dt>Household</dt>
                  <dd>{beneficiary.household.householdCode}</dd>
                </div>
                <div>
                  <dt>Site</dt>
                  <dd>{beneficiary.distributionSite}</dd>
                </div>
                <div>
                  <dt>Ration</dt>
                  <dd>{beneficiary.rationTier}</dd>
                </div>
              </dl>
              <div className="card-actions">
                <Button as={Link} variant="secondary" to={`/admin/beneficiaries/${beneficiary.id}`}>
                  Open record
                </Button>
                <Button
                  type="button"
                  disabled={beneficiary.currentEligibility?.status !== "eligible"}
                  onClick={() => handleIssue(beneficiary.id)}
                >
                  Issue now
                </Button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <div className="split-grid">
        <section className="panel-card">
          <p className="eyebrow">Redemption log</p>
          <h3>Deliveries</h3>
          <div className="simple-list">
            {redemptions.map((redemption) => (
              <div key={redemption.id} className="simple-list-row">
                <strong>{redemption.verificationReference}</strong>
                <span>{redemption.workerUsername}</span>
                <span>{new Date(redemption.createdAt).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="panel-card">
          <p className="eyebrow">Grievances</p>
          <h3>Open issues</h3>
          <div className="simple-list">
            {grievances.map((grievance) => (
              <div key={grievance.id} className="simple-list-row">
                <strong>{grievance.reason}</strong>
                <span>{grievance.createdBy}</span>
                <span>{grievance.status}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </Shell>
  );
}
