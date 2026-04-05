import { useState } from "react";
import { AlertTriangle, CheckCheck, QrCode, ScanSearch, Upload } from "lucide-react";
import Shell from "../components/Shell";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { extractVerificationInput } from "../utils/verificationInput";

const navItems = [{ to: "/worker", label: "Aid worker console", end: true, icon: ScanSearch }];

export default function WorkerPage({ session, onLogout }) {
  const [credentialText, setCredentialText] = useState("");
  const [credentialMetadata, setCredentialMetadata] = useState(null);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("");
  const [inputStatus, setInputStatus] = useState("");
  const [grievance, setGrievance] = useState({ reason: "Verification blocked", details: "" });

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setStatus("");
    setInputStatus("");
    try {
      const payload = await extractVerificationInput(file);
      setCredentialText(payload.credentialText);
      setCredentialMetadata(payload.credentialMetadata);
      setInputStatus(payload.sourceLabel);
    } catch (error) {
      setCredentialMetadata(null);
      setStatus(error.message);
    }
  };

  const handleVerify = async () => {
    setStatus("");
    try {
      const payload = await api.verifyCredential(session.accessToken, {
        credentialText,
        credentialMetadata,
      });
      setResult(payload);
    } catch (error) {
      setStatus(error.message);
    }
  };

  const handleRedeem = async () => {
    if (!result?.enrollmentSummary) {
      return;
    }
    setStatus("");
    try {
      await api.redeem(session.accessToken, {
        programEnrollmentId: result.enrollmentSummary.recordId,
        verificationReference: result.verificationReference,
        notes: "Confirmed through worker console.",
      });
      setResult((current) =>
        current
          ? {
              ...current,
              businessStatus: "already_redeemed",
              canRedeem: false,
              details: {
                ...(current.details || {}),
                redemptionStatus: "delivered",
              },
            }
          : current,
      );
      setStatus("Delivery confirmed and redemption recorded.");
    } catch (error) {
      setStatus(error.message);
    }
  };

  const handleGrievance = async () => {
    if (!result?.enrollmentSummary) {
      return;
    }
    setStatus("");
    try {
      await api.createGrievance(session.accessToken, {
        programEnrollmentId: result.enrollmentSummary.recordId,
        reason: grievance.reason,
        details: grievance.details,
      });
      setStatus("Grievance opened for follow-up.");
    } catch (error) {
      setStatus(error.message);
    }
  };

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Aid worker"
      subtitle="Verify beneficiary passes, confirm delivery, and record field issues."
      navItems={navItems}
    >
      {status ? <div className={`status-banner ${status.includes("confirmed") || status.includes("opened") ? "success" : "error"}`}>{status}</div> : null}

      <div className="split-grid">
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Verification input</p>
              <h3>RefuPass pass</h3>
            </div>
          </div>
          <p className="panel-copy">
            Paste the QR payload or upload a RefuPass PDF, QR image, or structured export from the gate.
          </p>
          <textarea
            className="credential-textarea"
            placeholder="Paste a RefuPass QR payload or upload PDF/PNG/JSON/TXT"
            value={credentialText}
            onChange={(event) => {
              setCredentialText(event.target.value);
              setCredentialMetadata(null);
            }}
          />
          <div className="card-actions">
            <label className="button button-secondary button-md file-button">
              <Upload size={16} strokeWidth={2.2} />
              Upload PDF/PNG/JSON/TXT
              <input type="file" accept="application/pdf,application/json,text/plain,image/png,image/jpeg,image/webp,.pdf,.png,.jpg,.jpeg,.webp,.json,.txt" onChange={handleFileUpload} hidden />
            </label>
            <Button type="button" onClick={handleVerify} disabled={!credentialText.trim()}>
              <QrCode size={16} strokeWidth={2.2} />
              Verify pass
            </Button>
          </div>
          {inputStatus ? <p className="panel-copy">{inputStatus}</p> : null}
        </section>

        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Verification result</p>
              <h3>Gate decision</h3>
            </div>
          </div>
          {result ? (
            <>
              <div className="detail-grid">
                <div>
                  <span>Verification mode</span>
                  <strong><Badge tone="neutral">{result.verificationMode}</Badge></strong>
                </div>
                <div>
                  <span>Cryptographic status</span>
                  <strong><Badge tone={result.cryptographicStatus === "valid" ? "eligible" : "neutral"}>{result.cryptographicStatus}</Badge></strong>
                </div>
                <div>
                  <span>Business status</span>
                  <strong><Badge tone={result.businessStatus === "valid" ? "eligible" : result.businessStatus === "already_redeemed" ? "warning" : "ineligible"}>{result.businessStatus}</Badge></strong>
                </div>
                <div>
                  <span>Cycle</span>
                  <strong>{result.aidCycle || "N/A"}</strong>
                </div>
                <div>
                  <span>Site</span>
                  <strong>{result.distributionSite || "N/A"}</strong>
                </div>
              </div>
              {result.enrollmentSummary ? (
                <div className="worker-summary">
                  <h4>{result.enrollmentSummary.fullName}</h4>
                  <p>
                    {result.enrollmentSummary.householdId} • {result.enrollmentSummary.rationTier}
                  </p>
                </div>
              ) : null}
              {["refupass_pass_qr", "printable_pass_qr"].includes(result.verificationMode) ? (
                <p className="panel-copy">
                  {result.verificationMode === "refupass_pass_qr"
                    ? "Verified from a RefuPass-issued QR or PDF."
                    : "Legacy printable pass format detected."}
                </p>
              ) : null}
              <p className="code-chip">{result.verificationReference}</p>
              {result.canRedeem ? (
                <div className="card-actions">
                  <Button type="button" onClick={handleRedeem}>
                    <CheckCheck size={16} strokeWidth={2.2} />
                    Confirm delivery
                  </Button>
                </div>
              ) : (
                <div className="status-banner success worker-readonly-state">
                  {result.businessStatus === "already_redeemed"
                    ? "Delivery is already recorded for this aid cycle."
                    : "This record cannot be redeemed from the current verification result."}
                </div>
              )}
            </>
          ) : (
            <p className="panel-copy">Run verification to continue.</p>
          )}
        </section>
      </div>

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Grievance capture</p>
            <h3>Flag a case for follow-up</h3>
          </div>
        </div>
        <p className="panel-copy">
          Use this when identity, eligibility, or delivery status needs manual review after the gate check.
        </p>
        <div className="split-grid tight">
          <label className="field-stack">
            Reason
            <input
              value={grievance.reason}
              onChange={(event) => setGrievance((current) => ({ ...current, reason: event.target.value }))}
            />
          </label>
          <label className="field-stack">
            Details
            <textarea
              rows="4"
              value={grievance.details}
              onChange={(event) => setGrievance((current) => ({ ...current, details: event.target.value }))}
            />
          </label>
        </div>
        <Button variant="secondary" type="button" onClick={handleGrievance} disabled={!result?.enrollmentSummary}>
          <AlertTriangle size={16} strokeWidth={2.2} />
          Open grievance
        </Button>
      </section>
    </Shell>
  );
}
