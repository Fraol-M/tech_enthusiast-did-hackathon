import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, Clock3, PackageCheck, Search, UserPlus, Users2 } from "lucide-react";
import Shell from "../components/Shell";
import StatCard from "../components/StatCard";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";

const navItems = [{ to: "/admin", label: "Admin dashboard", end: true, icon: Users2 }];

const defaultWorkerForm = {
  displayName: "",
  username: "",
  password: "",
};

export default function AdminDashboardPage({ session, onLogout }) {
  const ngoName = session.ngoName || "RefuPass NGO";
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [currentCycle, setCurrentCycle] = useState(null);
  const [redemptions, setRedemptions] = useState([]);
  const [grievances, setGrievances] = useState([]);
  const [aidWorkers, setAidWorkers] = useState([]);
  const [search, setSearch] = useState("");
  const [issuanceSession, setIssuanceSession] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [workerForm, setWorkerForm] = useState(defaultWorkerForm);
  const [workerLoading, setWorkerLoading] = useState(false);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [cycle, list, redemptionList, grievanceList, workerList] = await Promise.all([
        api.getCurrentCycle(session.accessToken),
        api.getBeneficiaries(session.accessToken),
        api.getRedemptions(session.accessToken),
        api.getGrievances(session.accessToken),
        api.getAidWorkers(session.accessToken),
      ]);
      setCurrentCycle(cycle);
      setBeneficiaries(list);
      setRedemptions(redemptionList);
      setGrievances(grievanceList);
      setAidWorkers(workerList);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
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
    } catch (error) {
      setStatus(error.message);
    } finally {
      setWorkerLoading(false);
    }
  };

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Admin"
      subtitle="Eligibility, issuance, staffing, and delivery."
      navItems={navItems}
      aside={
        <>
          {currentCycle ? (
            <div className="header-chip">
              <span>Current cycle</span>
              <strong>{currentCycle.name}</strong>
            </div>
          ) : null}
          <Button as={Link} to="/admin/beneficiaries/new">
            <UserPlus size={16} strokeWidth={2.2} />
            Add beneficiary
          </Button>
        </>
      }
    >
      {status ? <div className={`status-banner ${status.includes("added") ? "success" : "error"}`}>{status}</div> : null}

      <div className="stats-grid">
        <StatCard label="Eligible" value={eligibleCount} icon={Users2} />
        <StatCard label="Redeemed" value={redeemedCount} icon={PackageCheck} />
        <StatCard label="Grievances" value={grievances.length} icon={AlertTriangle} />
        <StatCard
          label="Beneficiaries"
          value={beneficiaries.length}
          hint={loading ? "Loading" : ngoName}
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
          <div className="section-heading">
            <div>
              <p className="eyebrow">Organization</p>
              <h3>Aid workers</h3>
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
          <div className="simple-list">
            {aidWorkers.map((worker) => (
              <div key={worker.id} className="simple-list-row">
                <strong>{worker.displayName}</strong>
                <span>{worker.username}</span>
                <span>{worker.ngoName}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <p className="eyebrow">Redemption log</p>
          <h3>Deliveries</h3>
          <div className="simple-list">
            {redemptions.map((redemption) => (
              <div key={redemption.id} className="simple-list-row">
                <strong>{redemption.verificationReference}</strong>
                <span>{ngoName} field team</span>
                <span>{new Date(redemption.createdAt).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel-card">
        <p className="eyebrow">Grievances</p>
        <h3>Open issues</h3>
        <div className="simple-list">
          {grievances.map((grievance) => (
            <div key={grievance.id} className="simple-list-row">
              <strong>{grievance.reason}</strong>
              <span>{ngoName} field team</span>
              <span>{grievance.status}</span>
            </div>
          ))}
        </div>
      </section>
    </Shell>
  );
}
