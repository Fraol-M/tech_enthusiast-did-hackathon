import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Users2, ArrowLeft } from "lucide-react";
import Shell from "../components/Shell";
import Button from "../components/Button";
import { api } from "../api/client";
import { describeIdentity, formatSubjectId } from "../utils/identity";

const navItems = [
  { to: "/platform", label: "Overview", end: true, icon: Users2 },
  { to: "/platform/people", label: "People Registry", end: true, icon: Users2 },
];

const defaultPersonForm = {
  fullName: "",
  phone: "",
  gender: "female",
  householdCode: "",
  familySize: 1,
  primaryContactName: "",
  settlement: "",
};

export default function PlatformPeoplePage({ session, onLogout }) {
  const [people, setPeople] = useState([]);
  const [personForm, setPersonForm] = useState(defaultPersonForm);
  const [status, setStatus] = useState("");
  const [statusTone, setStatusTone] = useState("success");
  const [loading, setLoading] = useState(true);
  const [personSubmitting, setPersonSubmitting] = useState(false);
  const [verificationSessionToken, setVerificationSessionToken] = useState("");
  const popupRef = useRef(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const payload = await api.getPeople(session.accessToken);
        setPeople(payload);
      } catch (error) {
        setStatusTone("error");
        setStatus(error.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [session.accessToken]);

  useEffect(() => {
    if (!verificationSessionToken) return undefined;

    let isCancelled = false;
    const pollVerification = async () => {
      try {
        const current = await api.getIdentityVerification(session.accessToken, verificationSessionToken);
        if (isCancelled) return;
        if (current.status === "completed" && current.person) {
          setPeople((existing) => {
            const next = existing.filter((person) => person.id !== current.person.id);
            return [...next, current.person].sort((left, right) => left.fullName.localeCompare(right.fullName));
          });
          setVerificationSessionToken("");
          setPersonSubmitting(false);
          setPersonForm(defaultPersonForm);
          setStatusTone("success");
          setStatus(`${current.person.fullName} verified with eSignet and added to the shared registry.`);
          if (popupRef.current && !popupRef.current.closed) popupRef.current.close();
          popupRef.current = null;
          return;
        }
        if (current.status === "failed") {
          setVerificationSessionToken("");
          setPersonSubmitting(false);
          setStatusTone("error");
          setStatus(current.errorMessage || "eSignet verification failed.");
          popupRef.current = null;
          return;
        }
        if (popupRef.current && popupRef.current.closed) {
          setVerificationSessionToken("");
          setPersonSubmitting(false);
          setStatusTone("error");
          setStatus("Verification window closed before the person was verified.");
          popupRef.current = null;
        }
      } catch (error) {
        if (!isCancelled) {
          setVerificationSessionToken("");
          setPersonSubmitting(false);
          setStatusTone("error");
          setStatus(error.message);
          popupRef.current = null;
        }
      }
    };

    pollVerification();
    const intervalId = window.setInterval(pollVerification, 1500);
    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, [session.accessToken, verificationSessionToken]);

  const handlePersonChange = (event) => {
    const { name, value } = event.target;
    setPersonForm((current) => ({
      ...current,
      [name]: name === "familySize" ? Number(value) : value,
    }));
  };

  const handlePersonSubmit = async (event) => {
    event.preventDefault();
    setPersonSubmitting(true);
    setStatusTone("success");
    setStatus("");
    try {
      const verification = await api.startIdentityVerification(session.accessToken, personForm);
      const popup = window.open(
        verification.authorizeUrl,
        "refupass-esignet-verification",
        "popup=yes,width=520,height=760",
      );
      if (!popup) {
        setPersonSubmitting(false);
        setStatusTone("error");
        setStatus("Allow popups to continue verification with eSignet.");
        return;
      }
      popupRef.current = popup;
      popup.focus();
      setVerificationSessionToken(verification.sessionToken);
      setStatus("Continue in the eSignet window to verify this person.");
    } catch (error) {
      setStatusTone("error");
      setStatus(error.message);
      setPersonSubmitting(false);
    }
  };

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="People Registry"
      subtitle="Verify people through eSignet and view the shared identity registry."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/platform"><ArrowLeft size={16} strokeWidth={1.5} /> Back</Button>}
    >
      {status ? <div className={`status-banner ${statusTone}`}>{status}</div> : null}

      <div className="split-grid">
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Shared identity</p>
              <h3>Verify person</h3>
            </div>
          </div>
          <form className="stacked-form" onSubmit={handlePersonSubmit}>
            <div className="detail-grid">
              <label>
                Full name
                <input name="fullName" value={personForm.fullName} onChange={handlePersonChange} required />
              </label>
              <label>
                Phone
                <input name="phone" value={personForm.phone} onChange={handlePersonChange} required />
              </label>
              <label>
                Gender
                <select name="gender" value={personForm.gender} onChange={handlePersonChange}>
                  <option value="female">female</option>
                  <option value="male">male</option>
                </select>
              </label>
              <label>
                Household code
                <input name="householdCode" value={personForm.householdCode} onChange={handlePersonChange} required />
              </label>
              <label>
                Family size
                <input type="number" min="1" name="familySize" value={personForm.familySize} onChange={handlePersonChange} required />
              </label>
              <label>
                Primary contact
                <input name="primaryContactName" value={personForm.primaryContactName} onChange={handlePersonChange} required />
              </label>
              <label>
                Settlement
                <input name="settlement" value={personForm.settlement} onChange={handlePersonChange} required />
              </label>
            </div>
            <Button type="submit" disabled={personSubmitting}>
              {personSubmitting ? "Waiting for verification..." : "Verify with eSignet"}
            </Button>
          </form>
        </section>

        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Shared registry</p>
              <h3>People</h3>
            </div>
          </div>
          <div className="simple-list">
            {loading ? (
              <div className="simple-list-row"><strong>Loading...</strong></div>
            ) : people.length ? (
              people.map((person) => (
                <div key={person.id} className="simple-list-row">
                  <strong>{person.fullName}</strong>
                  <span>{[person.personCode, describeIdentity(person)].filter(Boolean).join(" • ")}</span>
                  <span title={person.authSubject || undefined}>
                    {[person.household?.householdCode || "No household", person.authSubject ? formatSubjectId(person.authSubject) : null]
                      .filter(Boolean)
                      .join(" • ")}
                  </span>
                </div>
              ))
            ) : (
              <div className="simple-list-row"><strong>No people registered</strong></div>
            )}
          </div>
        </section>
      </div>
    </Shell>
  );
}
