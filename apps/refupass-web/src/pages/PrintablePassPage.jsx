import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { Copy, Printer, ShieldCheck } from "lucide-react";
import QRCode from "qrcode";
import Shell from "../components/Shell";
import { api } from "../api/client";
import Button from "../components/Button";

const navItems = [{ to: "/admin", label: "Admin dashboard", end: false, icon: ShieldCheck }];

export default function PrintablePassPage({ session, onLogout }) {
  const { id } = useParams();
  const location = useLocation();
  const [beneficiary, setBeneficiary] = useState(null);
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [status, setStatus] = useState("");
  const [copyStatus, setCopyStatus] = useState("");

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await api.getBeneficiary(session.accessToken, id);
        setBeneficiary(payload);
      } catch (error) {
        setStatus(error.message);
      }
    };
    run();
  }, [id, session.accessToken]);

  const printablePass = useMemo(() => {
    if (location.state?.printablePass) {
      return location.state.printablePass;
    }
    if (!beneficiary?.currentEligibility) {
      return null;
    }
    return {
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
      };
  }, [beneficiary, location.state]);

  useEffect(() => {
    if (!printablePass?.qrPayload) {
      return;
    }
    QRCode.toDataURL(printablePass.qrPayload, {
      margin: 1,
      color: {
        dark: "#14342B",
        light: "#F7F1E4",
      },
      width: 220,
    }).then(setQrDataUrl);
  }, [printablePass]);

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Printable pass"
      subtitle="Paper fallback."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to={`/admin/beneficiaries/${id}`}>Back to record</Button>}
    >
      {status ? <div className="status-banner error">{status}</div> : null}
      {printablePass ? (
        <section className="print-card panel-card">
          <div className="print-card-header">
            <div>
              <p className="eyebrow">Printable pass</p>
              <h3>{printablePass.fullName}</h3>
              <p>{printablePass.beneficiaryCode}</p>
            </div>
            {qrDataUrl ? <img src={qrDataUrl} alt="Printable verification QR" className="qr-image" /> : null}
          </div>
          <div className="detail-grid">
            <div>
              <span>Program</span>
              <strong>{printablePass.programName}</strong>
            </div>
            <div>
              <span>Distribution site</span>
              <strong>{printablePass.distributionSite}</strong>
            </div>
            <div>
              <span>Family size</span>
              <strong>{printablePass.familySize}</strong>
            </div>
            <div>
              <span>Ration tier</span>
              <strong>{printablePass.rationTier}</strong>
            </div>
            <div>
              <span>Valid until</span>
              <strong>{printablePass.validUntil}</strong>
            </div>
          </div>
          <label>
            Worker QR payload
            <textarea className="credential-textarea" rows="8" readOnly value={printablePass.qrPayload} />
          </label>
          <div className="card-actions">
            <Button
              variant="secondary"
              type="button"
              onClick={async () => {
                await navigator.clipboard.writeText(printablePass.qrPayload);
                setCopyStatus("QR payload copied.");
              }}
            >
              <Copy size={16} strokeWidth={2.2} />
              Copy QR payload
            </Button>
            <Button type="button" onClick={() => window.print()}>
              <Printer size={16} strokeWidth={2.2} />
              Print this pass
            </Button>
          </div>
          {copyStatus ? <p className="panel-copy">{copyStatus}</p> : null}
        </section>
      ) : (
        <section className="panel-card">Printable pass is available once eligibility is active.</section>
      )}
    </Shell>
  );
}
