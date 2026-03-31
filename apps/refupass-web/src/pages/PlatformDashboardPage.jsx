import { useEffect, useRef, useState } from "react";
import { Building2, ShieldCheck, UserPlus, Users2 } from "lucide-react";
import Shell from "../components/Shell";
import Button from "../components/Button";
import { api } from "../api/client";
import StatCard from "../components/StatCard";
import { describeIdentity, formatSubjectId } from "../utils/identity";

const navItems = [{ to: "/platform", label: "Platform dashboard", end: true, icon: ShieldCheck }];

const defaultForm = {
  ngoName: "",
  adminDisplayName: "",
  username: "",
  password: "",
};

const defaultPersonForm = {
  fullName: "",
  phone: "",
  gender: "female",
  householdCode: "",
  familySize: 1,
  primaryContactName: "",
  settlement: "",
};

export default function PlatformDashboardPage({ session, onLogout }) {
  const [ngos, setNgos] = useState([]);
  const [people, setPeople] = useState([]);
  const [form, setForm] = useState(defaultForm);
  const [personForm, setPersonForm] = useState(defaultPersonForm);
  const [status, setStatus] = useState("");
  const [statusTone, setStatusTone] = useState("success");
  const [loading, setLoading] = useState(true);
  const [ngoSubmitting, setNgoSubmitting] = useState(false);
  const [personSubmitting, setPersonSubmitting] = useState(false);
  const [verificationSessionToken, setVerificationSessionToken] = useState("");
  const popupRef = useRef(null);

  const loadPlatform = async () => {
    setLoading(true);
    try {
      const [ngoPayload, peoplePayload] = await Promise.all([
        api.getPlatformNgos(session.accessToken),
        api.getPeople(session.accessToken),
      ]);
      setNgos(ngoPayload);
      setPeople(peoplePayload);
    } catch (error) {
      setStatusTone("error");
      setStatus(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlatform();
  }, [session.accessToken]);

  useEffect(() => {
    if (!verificationSessionToken) {
      return undefined;
    }

    let isCancelled = false;
    const pollVerification = async () => {
      try {
        const current = await api.getIdentityVerification(session.accessToken, verificationSessionToken);
        if (isCancelled) {
          return;
        }
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
          if (popupRef.current && !popupRef.current.closed) {
            popupRef.current.close();
          }
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

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handlePersonChange = (event) => {
    const { name, value } = event.target;
    setPersonForm((current) => ({
      ...current,
      [name]: name === "familySize" ? Number(value) : value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setNgoSubmitting(true);
    setStatusTone("success");
    setStatus("");
    try {
      const created = await api.createPlatformNgo(session.accessToken, form);
      setNgos((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setForm(defaultForm);
      setStatus(`${created.name} registered with NGO admin ${created.adminDisplayName}.`);
    } catch (error) {
      setStatusTone("error");
      setStatus(error.message);
    } finally {
      setNgoSubmitting(false);
    }
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

  const ngoCount = ngos.length;
  const peopleCount = people.length;
  const adminCount = ngos.filter((ngo) => ngo.adminUsername).length;
  const workerCount = ngos.reduce((sum, ngo) => sum + ngo.aidWorkerCount, 0);
  const enrollmentCount = ngos.reduce((sum, ngo) => sum + ngo.enrollmentCount, 0);

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Platform"
      subtitle="Register NGOs, verify people through eSignet, and monitor workspace growth."
      navItems={navItems}
    >
      {status ? <div className={`status-banner ${statusTone}`}>{status}</div> : null}

      <div className="stats-grid">
        <StatCard label="NGOs" value={ngoCount} icon={Building2} />
        <StatCard label="People" value={peopleCount} icon={Users2} />
        <StatCard label="NGO admins" value={adminCount} icon={Users2} />
        <StatCard label="Aid workers" value={workerCount} icon={UserPlus} />
        <StatCard label="Enrollments" value={enrollmentCount} hint={loading ? "Loading" : "Across all NGOs"} icon={ShieldCheck} />
      </div>

      <div className="split-grid">
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Workspace setup</p>
              <h3>Register NGO</h3>
            </div>
          </div>
          <form className="stacked-form" onSubmit={handleSubmit}>
            <label>
              NGO name
              <input name="ngoName" value={form.ngoName} onChange={handleChange} required />
            </label>
            <label>
              NGO admin name
              <input name="adminDisplayName" value={form.adminDisplayName} onChange={handleChange} required />
            </label>
            <label>
              NGO admin username
              <input name="username" value={form.username} onChange={handleChange} required />
            </label>
            <label>
              Password
              <input type="password" name="password" value={form.password} onChange={handleChange} required />
            </label>
            <Button type="submit" disabled={ngoSubmitting}>
              {ngoSubmitting ? "Registering..." : "Create NGO workspace"}
            </Button>
          </form>
        </section>

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
      </div>

      <div className="split-grid">
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Current workspaces</p>
              <h3>NGO registry</h3>
            </div>
          </div>
          <div className="simple-list">
            {ngos.map((ngo) => (
              <div key={ngo.id} className="simple-list-row">
                <strong>{ngo.name}</strong>
                <span>{ngo.adminDisplayName || "No NGO admin"}</span>
                <span>{ngo.adminUsername || "unassigned"}</span>
                <span>{ngo.enrollmentCount} enrollments</span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Shared registry</p>
              <h3>People</h3>
            </div>
          </div>
          <div className="simple-list">
            {people.length ? (
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
              <div className="simple-list-row">
                <strong>No people registered</strong>
              </div>
            )}
          </div>
        </section>
      </div>
    </Shell>
  );
}
