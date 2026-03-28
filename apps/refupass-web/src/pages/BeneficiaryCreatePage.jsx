import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { UserPlus } from "lucide-react";
import Shell from "../components/Shell";
import Button from "../components/Button";
import { api } from "../api/client";

const navItems = [{ to: "/admin", label: "Admin dashboard", end: false, icon: UserPlus }];

const defaultForm = {
  beneficiaryCode: "",
  authSubject: "",
  fullName: "",
  phone: "",
  gender: "female",
  programName: "Emergency Food Assistance",
  distributionSite: "",
  rationTier: "",
  householdCode: "",
  familySize: 1,
  primaryContactName: "",
  settlement: "",
};

export default function BeneficiaryCreatePage({ session, onLogout }) {
  const ngoName = session.ngoName || "RefuPass NGO";
  const navigate = useNavigate();
  const [form, setForm] = useState(defaultForm);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: name === "familySize" ? Number(value) : value,
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setStatus("");
    try {
      const created = await api.createBeneficiary(session.accessToken, form);
      navigate(`/admin/beneficiaries/${created.id}`, { replace: true });
    } catch (error) {
      setStatus(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      title="Add beneficiary"
      subtitle="Register a new person into your NGO intake list."
      navItems={navItems}
      aside={<Button as={Link} variant="secondary" to="/admin">Back to dashboard</Button>}
    >
      {status ? <div className="status-banner error">{status}</div> : null}

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Intake</p>
            <h3>Beneficiary registration</h3>
          </div>
          <div className="header-chip">
            <span>NGO</span>
            <strong>{ngoName}</strong>
          </div>
        </div>

        <form className="stacked-form" onSubmit={submit}>
          <div className="detail-grid">
            <label>
              Full name
              <input name="fullName" value={form.fullName} onChange={updateField} required />
            </label>
            <label>
              Auth subject
              <input name="authSubject" value={form.authSubject} onChange={updateField} required />
            </label>
            <label>
              Beneficiary code
              <input name="beneficiaryCode" value={form.beneficiaryCode} onChange={updateField} required />
            </label>
            <label>
              Phone
              <input name="phone" value={form.phone} onChange={updateField} required />
            </label>
            <label>
              Gender
              <select name="gender" value={form.gender} onChange={updateField}>
                <option value="female">female</option>
                <option value="male">male</option>
              </select>
            </label>
            <label>
              Program
              <input name="programName" value={form.programName} onChange={updateField} required />
            </label>
            <label>
              Distribution site
              <input name="distributionSite" value={form.distributionSite} onChange={updateField} required />
            </label>
            <label>
              Ration tier
              <input name="rationTier" value={form.rationTier} onChange={updateField} required />
            </label>
            <label>
              Household code
              <input name="householdCode" value={form.householdCode} onChange={updateField} required />
            </label>
            <label>
              Family size
              <input type="number" min="1" name="familySize" value={form.familySize} onChange={updateField} required />
            </label>
            <label>
              Primary contact
              <input name="primaryContactName" value={form.primaryContactName} onChange={updateField} required />
            </label>
            <label>
              Settlement
              <input name="settlement" value={form.settlement} onChange={updateField} required />
            </label>
          </div>
          <div className="card-actions">
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : "Create beneficiary"}
            </Button>
            <Button as={Link} variant="secondary" to="/admin">
              Cancel
            </Button>
          </div>
        </form>
      </section>
    </Shell>
  );
}
