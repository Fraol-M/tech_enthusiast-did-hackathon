import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, UserPlus, FileDown, Users2, ArrowLeft } from "lucide-react";
import Shell from "../components/Shell";
import StatCard from "../components/StatCard";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { useToast } from "../components/ToastProvider";
import { describeIdentity, formatSubjectId } from "../utils/identity";

const navItems = [
  { to: "/admin", label: "Overview", end: true, icon: Users2 },
  { to: "/admin/roster", label: "Roster", end: true, icon: Users2 },
];

export default function AdminRosterPage({ session, onLogout }) {
  const [enrollments, setEnrollments] = useState([]);
  const [currentCycle, setCurrentCycle] = useState(null);
  const [search, setSearch] = useState("");
  const [issuanceSession, setIssuanceSession] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [cycle, list] = await Promise.all([
          api.getCurrentCycle(session.accessToken),
          api.getProgramEnrollments(session.accessToken),
        ]);
        setCurrentCycle(cycle);
        setEnrollments(list);
      } catch (error) {
        setStatus(error.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [session.accessToken]);

  const filteredEnrollments = useMemo(() => {
    if (!search.trim()) return enrollments;
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

  const handleIssue = async (programEnrollmentId) => {
    setStatus("");
    try {
      const sessionPayload = await api.createIssuanceSession(session.accessToken, programEnrollmentId);
      setIssuanceSession(sessionPayload);
      setStatus("RefuPass pass created. Open it, then print it or save it as a PDF.");
      showToast({
        title: "Beneficiary pass created",
        message: "The latest RefuPass pass is ready for printing or download.",
        tone: "success",
      });
    } catch (error) {
      setStatus(error.message);
      showToast({
        title: "Could not create pass",
        message: error.message,
        tone: "error",
      });
    }
  };

  const statusTone =
    status.includes("created") || status.includes("save") ? "success" : "error";
  const latestEnrollmentId = issuanceSession
    ? enrollments.find((item) => item.enrollmentCode === issuanceSession.printablePass.enrollmentCode)?.id
    : null;
  const latestPassLink = issuanceSession
    ? `/admin/enrollments/${latestEnrollmentId}/print?sessionToken=${encodeURIComponent(issuanceSession.sessionToken)}`
    : null;

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Enrollment Roster"
      subtitle="Search enrollments, view beneficiary profiles, and issue passes."
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
      {status ? <div className={`status-banner ${statusTone}`}>{status}</div> : null}

      {issuanceSession ? (
        <section className="panel-card session-panel">
          <div className="session-panel-copy">
            <p className="eyebrow">Latest RefuPass pass</p>
            <h3>{issuanceSession.credentialPreview.fullName}</h3>
            <p className="panel-copy">
              Pass ready for download, printing, or sharing as a PDF with the beneficiary.
            </p>
          </div>
          <div className="issuance-actions">
            {latestPassLink && latestEnrollmentId ? (
              <Button
                as={Link}
                to={latestPassLink}
                state={{ printablePass: issuanceSession.printablePass, sessionToken: issuanceSession.sessionToken }}
                variant="secondary"
              >
                <FileDown size={16} strokeWidth={2.2} />
                Open pass
              </Button>
            ) : null}
            <p className="code-chip">{issuanceSession.passId}</p>
          </div>
          <div className="detail-grid">
            <div><span>Person</span><strong title={issuanceSession.credentialPreview.subjectId}>{formatSubjectId(issuanceSession.credentialPreview.subjectId)}</strong></div>
            <div><span>Household</span><strong>{issuanceSession.credentialPreview.householdId}</strong></div>
            <div><span>Cycle</span><strong>{issuanceSession.credentialPreview.aidCycle}</strong></div>
            <div><span>Ration tier</span><strong>{issuanceSession.credentialPreview.rationTier}</strong></div>
            <div><span>Flow</span><strong>{issuanceSession.flowType.replaceAll("_", " ")}</strong></div>
            <div><span>Status</span><strong>{issuanceSession.status.replaceAll("_", " ")}</strong></div>
          </div>
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
                <div><dt>Person code</dt><dd>{enrollment.person.personCode}</dd></div>
                <div><dt>Enrollment</dt><dd>{enrollment.enrollmentCode}</dd></div>
                <div>
                  <dt>Identity</dt>
                  <dd title={enrollment.person.authSubject || undefined}>
                    {enrollment.person.authSubject
                      ? `${describeIdentity(enrollment.person)} • ${formatSubjectId(enrollment.person.authSubject)}`
                      : "Not linked"}
                  </dd>
                </div>
                <div><dt>Site</dt><dd>{enrollment.distributionSite}</dd></div>
                <div><dt>Ration</dt><dd>{enrollment.rationTier}</dd></div>
                <div><dt>Program</dt><dd>{enrollment.program.name}</dd></div>
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
                  Create pass
                </Button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </Shell>
  );
}
