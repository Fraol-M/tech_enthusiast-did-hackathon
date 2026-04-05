import { useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import { Download, Printer, ShieldCheck, Smartphone } from "lucide-react";
import { jsPDF } from "jspdf";
import QRCode from "qrcode";
import Shell from "../components/Shell";
import { api } from "../api/client";
import Button from "../components/Button";

const navItems = [{ to: "/admin", label: "Admin dashboard", end: false, icon: ShieldCheck }];

function buildFileStem(printablePass) {
  const safeName = printablePass.fullName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `${safeName || "beneficiary"}-${printablePass.passId}`;
}

function triggerDownload(dataUrl, filename) {
  const anchor = document.createElement("a");
  anchor.href = dataUrl;
  anchor.download = filename;
  anchor.click();
}

async function buildMobilePassImage(printablePass, qrDataUrl) {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Could not prepare the mobile pass image.");
  }

  canvas.width = 1080;
  canvas.height = 1920;

  context.fillStyle = "#f5efe2";
  context.fillRect(0, 0, canvas.width, canvas.height);

  context.fillStyle = "#14342B";
  context.fillRect(0, 0, canvas.width, 240);

  context.fillStyle = "#ffffff";
  context.font = "700 54px Georgia, serif";
  context.fillText("RefuProof", 72, 96);
  context.font = "400 30px Arial, sans-serif";
  context.fillText("Beneficiary mobile pass", 72, 148);

  context.fillStyle = "#fffaf1";
  context.fillRect(54, 204, 972, 1620);

  context.fillStyle = "#14342B";
  context.font = "700 52px Georgia, serif";
  context.fillText(printablePass.fullName, 96, 310);
  context.font = "400 28px Arial, sans-serif";
  context.fillStyle = "#5c5548";
  context.fillText(`${printablePass.personCode} • ${printablePass.enrollmentCode}`, 96, 358);

  const qrImage = await new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Could not render the QR for the mobile pass."));
    image.src = qrDataUrl;
  });
  context.drawImage(qrImage, 280, 420, 520, 520);

  const details = [
    ["Pass ID", printablePass.passId],
    ["Program", printablePass.programName],
    ["Aid cycle", printablePass.aidCycle],
    ["Distribution site", printablePass.distributionSite],
    ["Family size", String(printablePass.familySize)],
    ["Ration tier", printablePass.rationTier],
    ["Valid until", printablePass.validUntil],
  ];

  let y = 1040;
  for (const [label, value] of details) {
    context.fillStyle = "#7a6f61";
    context.font = "600 24px Arial, sans-serif";
    context.fillText(label.toUpperCase(), 96, y);
    context.fillStyle = "#14342B";
    context.font = "700 34px Arial, sans-serif";
    context.fillText(value, 96, y + 46);
    y += 124;
  }

  context.fillStyle = "#7a6f61";
  context.font = "400 24px Arial, sans-serif";
  context.fillText("Show this screen or the PDF at the gate for RefuProof verification.", 96, 1760);

  return canvas.toDataURL("image/png");
}

function downloadPassPdf(printablePass, qrDataUrl) {
  const pdf = new jsPDF({
    orientation: "portrait",
    unit: "pt",
    format: "a4",
  });

  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();

  pdf.setFillColor(20, 52, 43);
  pdf.rect(0, 0, pageWidth, 96, "F");

  pdf.setTextColor(255, 255, 255);
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(24);
  pdf.text("RefuProof", 44, 44);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(12);
  pdf.text("Beneficiary pass", 44, 66);

  pdf.setDrawColor(218, 206, 184);
  pdf.setFillColor(255, 250, 241);
  pdf.roundedRect(32, 118, pageWidth - 64, pageHeight - 172, 18, 18, "FD");

  pdf.setTextColor(20, 52, 43);
  pdf.setFont("times", "bold");
  pdf.setFontSize(22);
  pdf.text(printablePass.fullName, 56, 164);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(11);
  pdf.setTextColor(92, 85, 72);
  pdf.text(`${printablePass.personCode} • ${printablePass.enrollmentCode}`, 56, 184);

  pdf.addImage(qrDataUrl, "PNG", pageWidth - 224, 142, 148, 148);

  const details = [
    ["Pass ID", printablePass.passId],
    ["Program", printablePass.programName],
    ["Aid cycle", printablePass.aidCycle],
    ["Distribution site", printablePass.distributionSite],
    ["Family size", String(printablePass.familySize)],
    ["Ration tier", printablePass.rationTier],
    ["Valid until", printablePass.validUntil],
  ];

  let y = 236;
  for (const [label, value] of details) {
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(10);
    pdf.setTextColor(122, 111, 97);
    pdf.text(label.toUpperCase(), 56, y);

    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(14);
    pdf.setTextColor(20, 52, 43);
    pdf.text(value, 56, y + 20);
    y += 54;
  }

  pdf.setTextColor(122, 111, 97);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.text("Show this PDF or a printed copy at the gate for RefuProof verification.", 56, pageHeight - 72);

  pdf.save(`${buildFileStem(printablePass)}.pdf`);
}

export default function PrintablePassPage({ session, onLogout }) {
  const { id } = useParams();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [printablePass, setPrintablePass] = useState(location.state?.printablePass || null);
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [status, setStatus] = useState("");
  const [downloadStatus, setDownloadStatus] = useState("");
  const sessionToken = searchParams.get("sessionToken") || location.state?.sessionToken || null;

  useEffect(() => {
    const run = async () => {
      try {
        if (location.state?.printablePass) {
          setPrintablePass(location.state.printablePass);
          return;
        }
        if (!sessionToken) {
          setStatus("Create a RefuProof pass from the enrollment record before opening this page.");
          return;
        }
        const payload = await api.getIssuancePass(session.accessToken, sessionToken);
        setPrintablePass(payload);
      } catch (error) {
        setStatus(error.message);
      }
    };
    run();
  }, [location.state, session.accessToken, sessionToken]);

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
      title="RefuProof pass"
      subtitle="Print it, save it as a PDF, or generate a mobile pass for the beneficiary."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to={`/admin/enrollments/${id}`}>Back to record</Button>}
    >
      {status ? <div className="status-banner error">{status}</div> : null}
      {printablePass ? (
        <section className="print-card panel-card">
          <div className="print-card-header">
            <div>
              <p className="eyebrow">RefuProof-issued pass</p>
              <h3>{printablePass.fullName}</h3>
              <p>{[printablePass.personCode, printablePass.enrollmentCode].filter(Boolean).join(" • ")}</p>
            </div>
            {qrDataUrl ? <img src={qrDataUrl} alt="Printable verification QR" className="qr-image" /> : null}
          </div>
          <div className="detail-grid">
            <div>
              <span>Pass ID</span>
              <strong>{printablePass.passId}</strong>
            </div>
            <div>
              <span>Program</span>
              <strong>{printablePass.programName}</strong>
            </div>
            <div>
              <span>Aid cycle</span>
              <strong>{printablePass.aidCycle}</strong>
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
          <div className="card-actions">
            <Button
              variant="secondary"
              type="button"
              disabled={!qrDataUrl}
              onClick={() => {
                try {
                  downloadPassPdf(printablePass, qrDataUrl);
                  setDownloadStatus("PDF downloaded.");
                } catch (error) {
                  setDownloadStatus(error.message);
                }
              }}
            >
              <Download size={16} strokeWidth={2.2} />
              Download PDF
            </Button>
            <Button
              variant="secondary"
              type="button"
              disabled={!qrDataUrl}
              onClick={async () => {
                try {
                  const mobilePassImage = await buildMobilePassImage(printablePass, qrDataUrl);
                  triggerDownload(mobilePassImage, `${buildFileStem(printablePass)}-mobile-pass.png`);
                  setDownloadStatus("Mobile pass image downloaded.");
                } catch (error) {
                  setDownloadStatus(error.message);
                }
              }}
            >
              <Smartphone size={16} strokeWidth={2.2} />
              Save mobile pass
            </Button>
            <Button type="button" onClick={() => window.print()}>
              <Printer size={16} strokeWidth={2.2} />
              Print or save PDF
            </Button>
          </div>
          <p className="panel-copy">Use the PDF for printing, or save the mobile pass so the beneficiary can show it on their phone.</p>
          {downloadStatus ? <p className="panel-copy">{downloadStatus}</p> : null}
        </section>
      ) : (
        <section className="panel-card">Create a RefuProof pass from the enrollment record first.</section>
      )}
    </Shell>
  );
}
