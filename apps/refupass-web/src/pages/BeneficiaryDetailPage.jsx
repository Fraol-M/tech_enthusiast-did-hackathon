import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowUpRight, BadgeCheck, FileOutput, UserRound } from "lucide-react";
import Shell from "../components/Shell";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";

const navItems = [{ to: "/admin", label: "Admin dashboard", end: false, icon: UserRound }];

export default function BeneficiaryDetailPage({ session, onLogout }) {
  const { id } = useParams();
  const [beneficiary, setBeneficiary] = useState(null);
  const [eligibilityForm, setEligibilityForm] = useState({ status: "pending", notes: "" });
  const [issuanceSession, setIssuanceSession] = useState(null);
  const [status, setStatus] = useState("");

  const loadBeneficiary = async () => {
    try {
      const payload = await api.getBeneficiary(session.accessToken, id);
      setBeneficiary(payload);
      setEligibilityForm({
        status: payload.currentEligibility?.status || "pending",
        notes: payload.currentEligibility?.notes || "",
      });
    } catch (error) {
      setStatus(error.message);
    }
  };

  useEffect(() => {
    loadBeneficiary();
  }, [id, session.accessToken]);

  const printableState = useMemo(() => {
    if (!beneficiary?.currentEligibility) {
      return null;
    }
    return {
      printablePass: {
        beneficiaryCode: beneficiary.beneficiaryCode,
        fullName: beneficiary.fullName,
        programName: beneficiary.programName,
        aidCycle: "Current aid cycle",
        distributionSite: beneficiary.distributionSite,
        familySize: beneficiary.household.familySize,
        rationTier: beneficiary.rationTier,
        validUntil: beneficiary.currentEligibility.validUntil,
        qrPayload: JSON.stringify({
          recordType: "RefuPassPrintablePass",
          verificationMode: "printable_pass_qr",
          beneficiaryId: beneficiary.authSubject,
          beneficiaryCode: beneficiary.beneficiaryCode,
          householdId: beneficiary.household.householdCode,
          fullName: beneficiary.fullName,
          programName: beneficiary.programName,
          aidCycle: "Current aid cycle",
          distributionSite: beneficiary.distributionSite,
          familySize: beneficiary.household.familySize,
          rationTier: beneficiary.rationTier,
          entitlementStatus: beneficiary.currentEligibility.status,
          validUntil: beneficiary.currentEligibility.validUntil,
        }),
      },
    };
  }, [beneficiary]);

  const updateEligibility = async (event) => {
    event.preventDefault();
    setStatus("");
    try {
      await api.updateEligibility(session.accessToken, id, eligibilityForm);
      await loadBeneficiary();
      setStatus("Eligibility updated.");
    } catch (error) {
      setStatus(error.message);
    }
  };

  const startIssuance = async () => {
    setStatus("");
    try {
      const payload = await api.createIssuanceSession(session.accessToken, Number(id));
      setIssuanceSession(payload);
    } catch (error) {
      setStatus(error.message);
    }
  };

  if (!beneficiary) {
    return (
      <Shell
        session={session}
        onLogout={onLogout}
        title="Beneficiary record"
        subtitle="Loading beneficiary details..."
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
      title={beneficiary.fullName}
      subtitle={`${beneficiary.beneficiaryCode} • ${beneficiary.household.householdCode}`}
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/admin">Back to dashboard</Button>}
    >
      {status ? <div className={`status-banner ${status.includes("updated") ? "success" : "error"}`}>{status}</div> : null}

      <section className="panel-card beneficiary-hero">
        <div className="beneficiary-hero-copy">
          <p className="eyebrow">Beneficiary</p>
          <h3>{beneficiary.fullName}</h3>
          <p className="panel-copy">{beneficiary.programName}</p>
        </div>
        <div className="beneficiary-hero-facts">
          <div>
            <span className="eyebrow">Subject</span>
            <strong>{beneficiary.authSubject}</strong>
          </div>
          <div>
            <span className="eyebrow">Status</span>
            <Badge tone={beneficiary.currentEligibility?.status || "pending"}>
              {beneficiary.currentEligibility?.status || "pending"}
            </Badge>
          </div>
        </div>
      </section>

      <div className="split-grid">
        <section className="panel-card">
          <p className="eyebrow">Household summary</p>
          <h3>Profile</h3>
          <div className="detail-grid">
            <div>
              <span>Auth subject</span>
              <strong>{beneficiary.authSubject}</strong>
            </div>
            <div>
              <span>Program</span>
              <strong>{beneficiary.programName}</strong>
            </div>
            <div>
              <span>Distribution site</span>
              <strong>{beneficiary.distributionSite}</strong>
            </div>
            <div>
              <span>Ration tier</span>
              <strong>{beneficiary.rationTier}</strong>
            </div>
            <div>
              <span>Family size</span>
              <strong>{beneficiary.household.familySize}</strong>
            </div>
            <div>
              <span>Settlement</span>
              <strong>{beneficiary.household.settlement}</strong>
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
            <p className="eyebrow">Issuance handoff</p>
            <h3>Issuance</h3>
          </div>
          <div className="card-actions">
            <Button type="button" onClick={startIssuance}>
              <BadgeCheck size={16} strokeWidth={2.2} />
              Create issuance session
            </Button>
            <Button as={Link} variant="secondary" to={`/admin/beneficiaries/${id}/print`} state={printableState}>
              <FileOutput size={16} strokeWidth={2.2} />
              Printable fallback
            </Button>
          </div>
        </div>

        {issuanceSession ? (
          <div className="issuance-panel">
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
                <span>Beneficiary subject</span>
                <strong>{issuanceSession.credentialPreview.beneficiaryId}</strong>
              </div>
              <div>
                <span>Valid until</span>
                <strong>{issuanceSession.credentialPreview.validUntil}</strong>
              </div>
            </div>
            <ol className="instruction-list">
              {issuanceSession.instructions.map((instruction) => (
                <li key={instruction}>{instruction}</li>
              ))}
            </ol>
            <Button as="a" href={issuanceSession.launchUrl} target="_blank" rel="noreferrer">
              Open Inji Web
              <ArrowUpRight size={16} strokeWidth={2.2} />
            </Button>
          </div>
        ) : (
          <p className="panel-copy">Create a session to hand off to Inji Web.</p>
        )}
      </section>

      <div className="split-grid">
        <section className="panel-card">
          <p className="eyebrow">Redemptions</p>
          <h3>History</h3>
          <div className="simple-list">
            {beneficiary.redemptions.map((redemption) => (
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
            {beneficiary.grievances.map((grievance) => (
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
