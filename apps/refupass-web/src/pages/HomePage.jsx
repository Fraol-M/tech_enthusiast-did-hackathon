import { Link, useNavigate } from "react-router-dom";
import { User, Shield, Users } from "lucide-react";

export default function HomePage({ session }) {
  const navigate = useNavigate();

  const handleRoleSelection = (roleTab) => {
    navigate('/login', { state: { preselect: roleTab } });
  };

  return (
    <div className="elegant-home-layout">
      {/* Nvigation */}
      <nav className="elegant-nav">
        <div className="elegant-nav-brand">
          <img src="/refupass-mark.svg" alt="RefuPass" className="elegant-nav-logo" />
          <span className="elegant-brand-text">RefuPass</span>
        </div>
        <div className="elegant-nav-links">
          {session ? (
            <Link to="/platform" className="elegant-btn elegant-btn-solid">Return to Dashboard</Link>
          ) : (
            <Link to="/login" className="elegant-btn elegant-btn-outline">Sign In</Link>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <section className="elegant-hero">
        <div className="elegant-hero-bg">
          <img src="/istockphoto-640305394-612x612.jpg" alt="Humanitarian Aid Logistics" />
          <div className="elegant-hero-overlay"></div>
        </div>

        <div className="elegant-hero-content">
          <h1 className="elegant-title">Restoring Dignity Through Verification.</h1>
          <p className="elegant-subtitle">
            A secure, unified platform connecting global aid organizations with those who need it most.
          </p>

          <div className="elegant-role-cards">
            <button onClick={() => handleRoleSelection('aid_worker')} className="role-card">
              <User size={24} strokeWidth={1.5} className="role-icon" />
              <div className="role-text">
                <h3>Aid Worker</h3>
                <p>Field deployment access</p>
              </div>
            </button>
            <button onClick={() => handleRoleSelection('ngo_admin')} className="role-card">
              <Users size={24} strokeWidth={1.5} className="role-icon" />
              <div className="role-text">
                <h3>NGO Administration</h3>
                <p>Camp and resource management</p>
              </div>
            </button>
            <button onClick={() => handleRoleSelection('platform_admin')} className="role-card">
              <Shield size={24} strokeWidth={1.5} className="role-icon" />
              <div className="role-text">
                <h3>Platform Admin</h3>
                <p>Global oversight</p>
              </div>
            </button>
          </div>
        </div>
      </section>

      {/* Feature Section */}
      <section className="elegant-features">
        <div className="elegant-feature-row">
          <div className="elegant-feature-text">
            <h2>Compassionate Logistics</h2>
            <p>
              Our system guarantees that aid reaches the intended beneficiaries swiftly and securely. 
              By leveraging immutable identity tracking, we uphold the highest standards of trust and operational integrity within vulnerable communities.
            </p>
            <Link to="/login" className="elegant-link">Explore the platform →</Link>
          </div>
          <div className="elegant-feature-image">
            <img src="/unsplash_feature_1.jpg" alt="Distribution Effort" />
          </div>
        </div>
      </section>

      {/* Gallery Section */}
      <section className="elegant-gallery">
        <div className="elegant-gallery-grid">
          <div className="elegant-gallery-item">
            <img src="/unsplash_feature_1.jpg" alt="Humanitarian work" />
          </div>
          <div className="elegant-gallery-item">
            <img src="/unsplash_feature_2.jpg" alt="Care tracking" />
          </div>
          <div className="elegant-gallery-item">
            <img src="/unsplash_feature_3.jpg" alt="Dignified support" />
          </div>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="elegant-footer">
        <div className="footer-content">
          <p>© 2026 RefuPass Humanitarian Trust. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}
