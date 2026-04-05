import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search, UserPlus } from "lucide-react";
import Shell from "../components/Shell";
import Button from "../components/Button";
import { api } from "../api/client";
import { useToast } from "../components/ToastProvider";
import { describeIdentity, formatSubjectId } from "../utils/identity";

const navItems = [{ to: "/admin", label: "NGO dashboard", end: false, icon: UserPlus }];

const defaultForm = {
  programId: "",
  programName: "Emergency Food Assistance",
  distributionSite: "",
  rationTier: "",
  assistanceType: "food",
  notes: "",
};

export default function PersonEnrollmentCreatePage({ session, onLogout }) {
  const ngoName = session.ngoName || "RefuPass NGO";
  const navigate = useNavigate();
  const [people, setPeople] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [form, setForm] = useState(defaultForm);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(true);
  const { showToast } = useToast();

  const loadPeople = async (query = "") => {
    setSearching(true);
    try {
      const payload = await api.getPeople(session.accessToken, query);
      setPeople(payload);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setSearching(false);
    }
  };

  useEffect(() => {
    loadPeople();
    (async () => {
      try {
        const payload = await api.getPrograms(session.accessToken);
        setPrograms(payload);
        if (payload.length) {
          const [firstProgram] = payload;
          setForm((current) => ({
            ...current,
            programId: String(firstProgram.id),
            programName: firstProgram.name,
            assistanceType: firstProgram.assistanceType,
            distributionSite: firstProgram.defaultDistributionSite || "",
            rationTier: firstProgram.defaultRationTier || "",
          }));
        }
      } catch (error) {
        setStatus(error.message);
      }
    })();
  }, [session.accessToken]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadPeople(search);
    }, 200);

    return () => window.clearTimeout(timeoutId);
  }, [search]);

  const selectedPerson = useMemo(
    () => people.find((person) => person.id === selectedPersonId) || null,
    [people, selectedPersonId],
  );

  const updateField = (event) => {
    const { name, value } = event.target;
    if (name === "programId") {
      const selectedProgram = programs.find((program) => String(program.id) === value);
      setForm((current) => ({
        ...current,
        programId: value,
        programName: selectedProgram?.name || current.programName,
        assistanceType: selectedProgram?.assistanceType || current.assistanceType,
        distributionSite: selectedProgram?.defaultDistributionSite || "",
        rationTier: selectedProgram?.defaultRationTier || "",
      }));
      return;
    }
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!selectedPerson) {
      setStatus("Select a person before creating an enrollment.");
      showToast({
        title: "Select a person first",
        message: "Choose a verified person from the shared registry before creating an enrollment.",
        tone: "warning",
      });
      return;
    }
    setLoading(true);
    setStatus("");
    try {
      const enrollment = await api.createProgramEnrollment(session.accessToken, {
        personId: selectedPerson.id,
        programId: form.programId ? Number(form.programId) : null,
        programName: programs.length ? null : form.programName,
        assistanceType: form.assistanceType,
        distributionSite: form.distributionSite,
        rationTier: form.rationTier,
        notes: form.notes || "Created through the NGO enrollment flow.",
      });
      showToast({
        title: "Enrollment ready",
        message: `${selectedPerson.fullName} is now attached to ${enrollment.program.name}.`,
        tone: "success",
      });
      navigate(`/admin/enrollments/${enrollment.id}`, { replace: true });
    } catch (error) {
      setStatus(error.message);
      showToast({
        title: "Could not create enrollment",
        message: error.message,
        tone: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Enroll person"
      subtitle="Search the shared registry, then attach the person to your NGO program."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/admin">Back to dashboard</Button>}
    >
      {status ? <div className="status-banner error">{status}</div> : null}

      <div className="split-grid">
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Shared registry</p>
              <h3>Select person</h3>
            </div>
          </div>
          <p className="panel-copy">
            Find a previously verified person by settlement first, then by name or person code, and attach them to your NGO program.
          </p>
          <div className="search-wrap">
            <Search size={16} strokeWidth={2.2} />
            <input
              className="search-input"
              placeholder="Search by settlement, name, household code, or person code"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <div className="simple-list">
            {searching ? (
              <div className="simple-list-row">
                <strong>Loading people...</strong>
              </div>
            ) : people.length ? (
              people.map((person) => (
                <button
                  key={person.id}
                  type="button"
                  className={`simple-list-row button-reset ${selectedPersonId === person.id ? "active-list-row" : ""}`}
                  onClick={() => setSelectedPersonId(person.id)}
                >
                  <strong>{person.fullName}</strong>
                  <span>{[person.personCode, describeIdentity(person)].filter(Boolean).join(" • ")}</span>
                  <span title={person.authSubject || undefined}>
                    {[person.household?.settlement || "No settlement", person.household?.householdCode || "No household", person.authSubject ? formatSubjectId(person.authSubject) : null]
                      .filter(Boolean)
                      .join(" • ")}
                  </span>
                </button>
              ))
            ) : (
              <div className="simple-list-row">
                <strong>No people found</strong>
                <span>Use the platform workspace to register a new person.</span>
              </div>
            )}
          </div>
        </section>

        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">NGO program</p>
              <h3>Create enrollment</h3>
            </div>
            <div className="header-chip">
              <span>NGO</span>
              <strong>{ngoName}</strong>
            </div>
          </div>

          {selectedPerson ? (
            <>
              <p className="panel-copy">Selected person is ready to be enrolled into the program below.</p>
              <div className="detail-grid">
                <div>
                  <span>Person</span>
                  <strong>{selectedPerson.fullName}</strong>
                </div>
                <div>
                  <span>Person code</span>
                  <strong>{selectedPerson.personCode}</strong>
                </div>
                <div>
                  <span>Identity</span>
                  <strong title={selectedPerson.authSubject || undefined}>
                    {selectedPerson.authSubject ? `${describeIdentity(selectedPerson)} • ${formatSubjectId(selectedPerson.authSubject)}` : "Not linked"}
                  </strong>
                </div>
                <div>
                  <span>Household</span>
                  <strong>{selectedPerson.household?.householdCode || "Not linked"}</strong>
                </div>
              </div>
            </>
          ) : (
            <p className="panel-copy">Select a person from the shared registry to continue.</p>
          )}

          <form className="stacked-form" onSubmit={submit}>
            {programs.length ? (
              <label>
                Program
                <select name="programId" value={form.programId} onChange={updateField} required>
                  {programs.map((program) => (
                    <option key={program.id} value={program.id}>
                      {program.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <>
                <label>
                  Program
                  <input name="programName" value={form.programName} onChange={updateField} required />
                </label>
                <label>
                  Assistance type
                  <select name="assistanceType" value={form.assistanceType} onChange={updateField}>
                    <option value="food">food</option>
                    <option value="cash">cash</option>
                    <option value="health">health</option>
                    <option value="shelter">shelter</option>
                  </select>
                </label>
              </>
            )}
            <label>
              Distribution site
              <input name="distributionSite" value={form.distributionSite} onChange={updateField} required />
            </label>
            <label>
              Ration tier
              <input name="rationTier" value={form.rationTier} onChange={updateField} required />
            </label>
            <label>
              Notes
              <textarea rows="4" name="notes" value={form.notes} onChange={updateField} />
            </label>
            <div className="card-actions">
              <Button type="submit" disabled={loading || !selectedPerson}>
                {loading ? "Saving..." : "Create enrollment"}
              </Button>
              <Button as={Link} variant="secondary" to="/admin">
                Cancel
              </Button>
            </div>
          </form>
        </section>
      </div>
    </Shell>
  );
}
