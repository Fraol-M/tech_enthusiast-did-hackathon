import { useState } from "react";
import { AlertTriangle, CheckCheck, QrCode, ScanSearch, Upload } from "lucide-react";
import Shell from "../components/Shell";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";

const navItems = [{ to: "/worker", label: "Aid worker console", end: true, icon: ScanSearch }];

export default function WorkerPage({ session, onLogout }) {
  const [credentialText, setCredentialText] = useState("");
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("");
  const [grievance, setGrievance] = useState({ reason: "Verification blocked", details: "" });

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const text = await file.text();
    setCredentialText(text);
  };

  const handleVerify = async () => {
    setStatus("");
    try {
      const payload = await api.verifyCredential(session.accessToken, {
        credentialText,
      });
      setResult(payload);
    } catch (error) {
      setStatus(error.message);
    }
  };

  const handleRedeem = async () => {
    if (!result?.beneficiarySummary) {
      return;
    }
    setStatus("");
    try {
      await api.redeem(session.accessToken, {
        beneficiaryId: result.beneficiarySummary.recordId,
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
    if (!result?.beneficiarySummary) {
      return;
    }
    setStatus("");
    try {
      await api.createGrievance(session.accessToken, {
        beneficiaryId: result.beneficiarySummary.recordId,
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
      subtitle="Verify and redeem."
      navItems={navItems}
    >
      {status ? <div className={`status-banner ${status.includes("confirmed") || status.includes("opened") ? "success" : "error"}`}>{status}</div> : null}

      <div className="split-grid">
        <section className="panel-card">
          <p className="eyebrow">Input</p>
          <h3>Pass or VC</h3>
          <textarea
            className="credential-textarea"
            placeholder="Paste pass QR payload or VC JSON"
            value={credentialText}
            onChange={(event) => setCredentialText(event.target.value)}
          />
          <div className="card-actions">
            <label className="button button-secondary button-md file-button">
              <Upload size={16} strokeWidth={2.2} />
              Upload JSON/TXT
              <input type="file" accept="application/json,text/plain,.json,.txt" onChange={handleFileUpload} hidden />
            </label>
            <Button type="button" onClick={handleVerify}>
              <QrCode size={16} strokeWidth={2.2} />
              Run verification
            </Button>
          </div>
        </section>

        <section className="panel-card">
          <p className="eyebrow">Result</p>
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
              {result.beneficiarySummary ? (
                <div className="worker-summary">
                  <h4>{result.beneficiarySummary.fullName}</h4>
                  <p>
                    {result.beneficiarySummary.householdId} • {result.beneficiarySummary.rationTier}
                  </p>
                </div>
              ) : null}
              {result.verificationMode === "printable_pass_qr" ? (
                <p className="panel-copy">Printable pass fallback.</p>
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
        <p className="eyebrow">Grievance capture</p>
        <h3>Open grievance</h3>
        <div className="split-grid tight">
          <label>
            Reason
            <input
              value={grievance.reason}
              onChange={(event) => setGrievance((current) => ({ ...current, reason: event.target.value }))}
            />
          </label>
          <label>
            Details
            <textarea
              rows="4"
              value={grievance.details}
              onChange={(event) => setGrievance((current) => ({ ...current, details: event.target.value }))}
            />
          </label>
        </div>
        <Button variant="secondary" type="button" onClick={handleGrievance} disabled={!result?.beneficiarySummary}>
          <AlertTriangle size={16} strokeWidth={2.2} />
          Open grievance
        </Button>
      </section>
    </Shell>
  );
}
