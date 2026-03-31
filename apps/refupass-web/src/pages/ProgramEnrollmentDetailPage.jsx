import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowUpRight, BadgeCheck, UserRound } from "lucide-react";
import Shell from "../components/Shell";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { describeIdentity, formatSubjectId } from "../utils/identity";

const navItems = [{ to: "/admin", label: "Admin dashboard", end: false, icon: UserRound }];

export default function ProgramEnrollmentDetailPage({ session, onLogout }) {
  const { id } = useParams();
  const [enrollment, setEnrollment] = useState(null);
  const [eligibilityForm, setEligibilityForm] = useState({ status: "pending", notes: "" });
  const [issuanceSession, setIssuanceSession] = useState(null);
  const [status, setStatus] = useState("");
  const popupRef = useRef(null);
  const popupStateRef = useRef({ sessionToken: null, closureHandled: false });

  const loadEnrollment = async () => {
    try {
      const payload = await api.getProgramEnrollment(session.accessToken, id);
      setEnrollment(payload);
      setEligibilityForm({
        status: payload.currentEligibility?.status || "pending",
        notes: payload.currentEligibility?.notes || "",
      });
    } catch (error) {
      setStatus(error.message);
    }
  };

  useEffect(() => {
    loadEnrollment();
  }, [id, session.accessToken]);

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
          setStatus("Wallet window closed. RefuPass kept the entitlement ready for later verification.");
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

  const updateEligibility = async (event) => {
    event.preventDefault();
    setStatus("");
    try {
      await api.updateProgramEnrollmentEligibility(session.accessToken, id, eligibilityForm);
      await loadEnrollment();
      setStatus("Eligibility updated.");
    } catch (error) {
      setStatus(error.message);
    }
  };

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

  const startIssuance = async () => {
    setStatus("");
    try {
      const payload = await api.createIssuanceSession(session.accessToken, Number(id));
      setIssuanceSession(payload);
      await launchWalletPopup(payload);
    } catch (error) {
      setStatus(error.message);
    }
  };

  if (!enrollment) {
    return (
      <Shell
        session={session}
        onLogout={onLogout}
        title="Person profile"
        subtitle="Loading shared identity and enrollment details..."
        navItems={navItems}
      >
        {status ? <div className="status-banner error">{status}</div> : <div className="panel-card">Loading...</div>}
      </Shell>
    );
  }

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title={enrollment.person.fullName}
      subtitle={[enrollment.person.personCode, enrollment.enrollmentCode, enrollment.person.household?.householdCode].filter(Boolean).join(" • ")}
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/admin">Back to dashboard</Button>}
    >
      {status ? <div className={`status-banner ${status.includes("updated") || status.includes("ready") || status.includes("tracking") || status.includes("verified") || status.includes("closed") ? "success" : "error"}`}>{status}</div> : null}

      <section className="panel-card beneficiary-hero">
        <div className="beneficiary-hero-copy">
          <p className="eyebrow">Shared person</p>
          <h3>{enrollment.person.fullName}</h3>
          <p className="panel-copy">{enrollment.program.name}</p>
        </div>
        <div className="beneficiary-hero-facts">
          <div>
            <span className="eyebrow">Person code</span>
            <strong>{enrollment.person.personCode}</strong>
          </div>
          <div>
            <span className="eyebrow">Status</span>
            <Badge tone={enrollment.currentEligibility?.status || "pending"}>
              {enrollment.currentEligibility?.status || "pending"}
            </Badge>
          </div>
        </div>
      </section>

      <div className="split-grid">
        <section className="panel-card">
          <p className="eyebrow">Identity and enrollment</p>
          <h3>Profile</h3>
          <div className="detail-grid">
            <div>
              <span>Person code</span>
              <strong>{enrollment.person.personCode}</strong>
            </div>
            <div>
              <span>Enrollment</span>
              <strong>{enrollment.enrollmentCode}</strong>
            </div>
            <div>
              <span>Identity</span>
              <strong title={enrollment.person.authSubject || undefined}>
                {enrollment.person.authSubject
                  ? `${describeIdentity(enrollment.person)} • ${formatSubjectId(enrollment.person.authSubject)}`
                  : "Not linked"}
              </strong>
            </div>
            <div>
              <span>Program</span>
              <strong>{enrollment.program.name}</strong>
            </div>
            <div>
              <span>Distribution site</span>
              <strong>{enrollment.distributionSite}</strong>
            </div>
            <div>
              <span>Ration tier</span>
              <strong>{enrollment.rationTier}</strong>
            </div>
            <div>
              <span>Household</span>
              <strong>{enrollment.person.household?.householdCode || "Not linked"}</strong>
            </div>
            <div>
              <span>Family size</span>
              <strong>{enrollment.person.household?.familySize || 0}</strong>
            </div>
            <div>
              <span>Settlement</span>
              <strong>{enrollment.person.household?.settlement || "Not linked"}</strong>
            </div>
          </div>
        </section>

        <section className="panel-card">
          <p className="eyebrow">Current cycle eligibility</p>
          <h3>Eligibility</h3>
          <form className="stacked-form" onSubmit={updateEligibility}>
            <label>
              Status
              <select
                value={eligibilityForm.status}
                onChange={(event) =>
                  setEligibilityForm((current) => ({ ...current, status: event.target.value }))
                }
              >
                <option value="eligible">eligible</option>
                <option value="pending">pending</option>
                <option value="ineligible">ineligible</option>
              </select>
            </label>
            <label>
              Notes
              <textarea
                rows="4"
                value={eligibilityForm.notes}
                onChange={(event) =>
                  setEligibilityForm((current) => ({ ...current, notes: event.target.value }))
                }
              />
            </label>
            <Button type="submit">
              Save cycle decision
            </Button>
          </form>
        </section>
      </div>

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Entitlement issuance</p>
            <h3>Issue credential</h3>
          </div>
          <div className="card-actions">
            <Button type="button" onClick={startIssuance}>
              <BadgeCheck size={16} strokeWidth={2.2} />
              Create issuance session
            </Button>
          </div>
        </div>

        {issuanceSession ? (
          <div className="issuance-panel">
            <div className="status-banner success">RefuPass has prepared this entitlement for the verified shared person.</div>
            <div className="detail-grid">
              <div>
                <span>Issuer</span>
                <strong>{issuanceSession.issuerId}</strong>
              </div>
              <div>
                <span>Credential config</span>
                <strong>{issuanceSession.credentialConfigurationId}</strong>
              </div>
              <div>
                <span>Person subject</span>
                <strong title={issuanceSession.credentialPreview.subjectId}>
                  {formatSubjectId(issuanceSession.credentialPreview.subjectId)}
                </strong>
              </div>
              <div>
                <span>Valid until</span>
                <strong>{issuanceSession.credentialPreview.validUntil}</strong>
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
            <ol className="instruction-list">
              {issuanceSession.instructions.map((instruction) => (
                <li key={instruction}>{instruction}</li>
              ))}
            </ol>
            {issuanceSession.externalWalletFlow ? (
              <div className="card-actions">
                <Button type="button" onClick={() => launchWalletPopup(issuanceSession)} variant="secondary">
                  {issuanceSession.externalWalletFlow.label}
                  <ArrowUpRight size={16} strokeWidth={2.2} />
                </Button>
                <p className="panel-copy">{issuanceSession.externalWalletFlow.note}</p>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="panel-copy">Create a session when this eligible enrollment is ready for issuer-managed credential delivery.</p>
        )}
      </section>

      <div className="split-grid">
        <section className="panel-card">
          <p className="eyebrow">Redemptions</p>
          <h3>History</h3>
          <div className="simple-list">
            {enrollment.redemptions.map((redemption) => (
              <div key={redemption.id} className="simple-list-row">
                <strong>{redemption.verificationReference}</strong>
                <span>{redemption.deliveryStatus}</span>
                <span>{new Date(redemption.createdAt).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="panel-card">
          <p className="eyebrow">Grievances</p>
          <h3>Follow-up</h3>
          <div className="simple-list">
            {enrollment.grievances.map((grievance) => (
              <div key={grievance.id} className="simple-list-row">
                <strong>{grievance.reason}</strong>
                <span>{grievance.status}</span>
                <span>{new Date(grievance.createdAt).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </Shell>
  );
}
