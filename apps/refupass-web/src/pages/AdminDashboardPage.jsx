import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, Clock3, PackageCheck, Search, UserPlus, Users2 } from "lucide-react";
import Shell from "../components/Shell";
import StatCard from "../components/StatCard";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { describeIdentity, formatSubjectId } from "../utils/identity";

const navItems = [{ to: "/admin", label: "NGO dashboard", end: true, icon: Users2 }];

const defaultWorkerForm = {
  displayName: "",
  username: "",
  password: "",
};

export default function AdminDashboardPage({ session, onLogout }) {
  const ngoName = session.ngoName || "RefuPass NGO";
  const [enrollments, setEnrollments] = useState([]);
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
  const popupRef = useRef(null);
  const popupStateRef = useRef({ sessionToken: null, closureHandled: false });

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [cycle, list, redemptionList, grievanceList, workerList] = await Promise.all([
        api.getCurrentCycle(session.accessToken),
        api.getProgramEnrollments(session.accessToken),
        api.getRedemptions(session.accessToken),
        api.getGrievances(session.accessToken),
        api.getAidWorkers(session.accessToken),
      ]);
      setCurrentCycle(cycle);
      setEnrollments(list);
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

  useEffect(() => {
    if (!issuanceSession?.sessionToken) {
      return undefined;
    }

    if (popupStateRef.current.sessionToken !== issuanceSession.sessionToken) {
      popupStateRef.current = { sessionToken: issuanceSession.sessionToken, closureHandled: false };
    }

    let cancelled = false;
    const pollIssuance = async () => {
      try {
        const current = await api.getIssuanceSession(session.accessToken, issuanceSession.sessionToken);
        if (cancelled) {
          return;
        }
        setIssuanceSession(current);

        if (
          popupRef.current &&
          popupRef.current.closed &&
          !popupStateRef.current.closureHandled &&
          ["holder_in_progress", "entitlement_ready"].includes(current.status)
        ) {
          popupStateRef.current.closureHandled = true;
          const closedSession = await api.updateIssuanceSessionStatus(
            session.accessToken,
            issuanceSession.sessionToken,
            "wallet_window_closed",
          );
          if (cancelled) {
            return;
          }
          setIssuanceSession(closedSession);
          setStatus("Wallet window closed. The entitlement remains ready in RefuPass.");
        }

        if (["credential_verified", "redeemed"].includes(current.status)) {
          if (popupRef.current && !popupRef.current.closed) {
            popupRef.current.close();
          }
          popupRef.current = null;
        }
      } catch (error) {
        if (!cancelled) {
          setStatus(error.message);
        }
      }
    };

    pollIssuance();
    const intervalId = window.setInterval(pollIssuance, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [issuanceSession?.sessionToken, session.accessToken]);

  const filteredEnrollments = useMemo(() => {
    if (!search.trim()) {
      return enrollments;
    }
    const needle = search.toLowerCase();
    return enrollments.filter((enrollment) =>
      [
        enrollment.person.fullName,
        enrollment.person.authSubject,
        enrollment.person.personCode,
        enrollment.enrollmentCode,
        enrollment.program.name,
      ]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(needle)),
    );
  }, [enrollments, search]);

  const peopleCount = new Set(enrollments.map((enrollment) => enrollment.person.id)).size;
  const eligibleCount = enrollments.filter(
    (enrollment) => enrollment.currentEligibility?.status === "eligible",
  ).length;
  const redeemedCount = enrollments.filter((enrollment) => enrollment.currentRedemption).length;

  const launchWalletPopup = async (sessionPayload) => {
    const walletUrl = sessionPayload.externalWalletFlow?.url;
    if (!walletUrl) {
      setStatus("Issuance session is ready.");
      return;
    }
    const popup = window.open(
      walletUrl,
      "refupass-wallet-issuance",
      "popup=yes,width=520,height=760",
    );
    if (!popup) {
      setStatus("Allow popups to continue the wallet issuance flow.");
      return;
    }
    popupRef.current = popup;
    popup.focus();
    popupStateRef.current = { sessionToken: sessionPayload.sessionToken, closureHandled: false };
    if (sessionPayload.status !== "holder_in_progress") {
      const inProgress = await api.updateIssuanceSessionStatus(
        session.accessToken,
        sessionPayload.sessionToken,
        "holder_in_progress",
      );
      setIssuanceSession(inProgress);
    } else {
      setIssuanceSession(sessionPayload);
    }
    setStatus("Continue in the wallet popup. RefuPass will keep tracking this issuance session.");
  };

  const handleIssue = async (programEnrollmentId) => {
    setStatus("");
    try {
      const sessionPayload = await api.createIssuanceSession(session.accessToken, programEnrollmentId);
      setIssuanceSession(sessionPayload);
      await launchWalletPopup(sessionPayload);
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
      title="NGO admin"
      subtitle="Shared people, NGO enrollments, issuance, staffing, and delivery."
      navItems={navItems}
      aside={
        <>
          {currentCycle ? (
            <div className="header-chip">
              <span>Current cycle</span>
              <strong>{currentCycle.name}</strong>
            </div>
          ) : null}
          <Button as={Link} to="/admin/enrollments/new">
            <UserPlus size={16} strokeWidth={2.2} />
            Enroll person
          </Button>
        </>
      }
    >
      {status ? <div className={`status-banner ${status.includes("added") || status.includes("tracking") || status.includes("ready") || status.includes("closed") || status.includes("verified") ? "success" : "error"}`}>{status}</div> : null}

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

      {issuanceSession ? (
        <section className="panel-card session-panel">
          <div className="session-panel-copy">
            <p className="eyebrow">Latest issuance</p>
            <h3>{issuanceSession.credentialPreview.fullName}</h3>
            <p className="panel-copy">Entitlement prepared in RefuPass for the verified shared person.</p>
          </div>
          <div className="issuance-actions">
            {issuanceSession.externalWalletFlow ? (
              <Button as="a" href={issuanceSession.externalWalletFlow.url} target="_blank" rel="noreferrer" variant="secondary">
                {issuanceSession.externalWalletFlow.label}
                <ArrowUpRight size={16} strokeWidth={2.2} />
              </Button>
            ) : null}
            <p className="code-chip">{issuanceSession.credentialConfigurationId}</p>
          </div>
          <div className="detail-grid">
            <div>
              <span>Person</span>
              <strong title={issuanceSession.credentialPreview.subjectId}>
                {formatSubjectId(issuanceSession.credentialPreview.subjectId)}
              </strong>
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
            <div>
              <span>Flow</span>
              <strong>{issuanceSession.flowType.replaceAll("_", " ")}</strong>
            </div>
            <div>
              <span>Session status</span>
              <strong>{issuanceSession.status.replaceAll("_", " ")}</strong>
            </div>
          </div>
          {issuanceSession.externalWalletFlow ? (
            <div className="card-actions">
              <Button type="button" onClick={() => launchWalletPopup(issuanceSession)} variant="secondary">
                {issuanceSession.externalWalletFlow.label}
                <ArrowUpRight size={16} strokeWidth={2.2} />
              </Button>
              <p className="panel-copy">{issuanceSession.externalWalletFlow.note}</p>
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">People and enrollments</p>
            <h3>Current NGO roster</h3>
          </div>
          <div className="search-wrap">
            <Search size={16} strokeWidth={2.2} />
            <input
              className="search-input"
              placeholder="Search by name, subject, person code, or enrollment"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>
        <div className="beneficiary-grid">
          {filteredEnrollments.map((enrollment) => (
            <article key={enrollment.id} className="beneficiary-card">
              <div className="card-header-row">
                <div>
                  <h4>{enrollment.person.fullName}</h4>
                  <p>{[enrollment.person.personCode, enrollment.enrollmentCode].filter(Boolean).join(" • ")}</p>
                </div>
                <Badge tone={enrollment.currentEligibility?.status || "pending"}>
                  {enrollment.currentEligibility?.status || "pending"}
                </Badge>
              </div>
              <dl className="card-facts">
                <div>
                  <dt>Person code</dt>
                  <dd>{enrollment.person.personCode}</dd>
                </div>
                <div>
                  <dt>Enrollment</dt>
                  <dd>{enrollment.enrollmentCode}</dd>
                </div>
                <div>
                  <dt>Subject</dt>
                  <dd title={enrollment.person.authSubject || undefined}>
                    {enrollment.person.authSubject ? `${describeIdentity(enrollment.person)} • ${formatSubjectId(enrollment.person.authSubject)}` : "Not linked"}
                  </dd>
                </div>
                <div>
                  <dt>Site</dt>
                  <dd>{enrollment.distributionSite}</dd>
                </div>
                <div>
                  <dt>Ration</dt>
                  <dd>{enrollment.rationTier}</dd>
                </div>
                <div>
                  <dt>Program</dt>
                  <dd>{enrollment.program.name}</dd>
                </div>
              </dl>
              <div className="card-actions">
                <Button as={Link} variant="secondary" to={`/admin/enrollments/${enrollment.id}`}>
                  Open profile
                </Button>
                <Button
                  type="button"
                  disabled={enrollment.currentEligibility?.status !== "eligible"}
                  onClick={() => handleIssue(enrollment.id)}
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
