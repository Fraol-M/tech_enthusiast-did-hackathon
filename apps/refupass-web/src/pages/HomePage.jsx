import { Link, useNavigate } from "react-router-dom";
import { User, Shield, Users, ArrowRight, ShieldCheck, Heart, Fingerprint } from "lucide-react";

export default function HomePage({ session }) {
  const navigate = useNavigate();
  const dashboardPath =
    session?.role === "platform_admin" ? "/platform" : session?.role === "aid_worker" ? "/worker" : "/admin";

  const handleRoleSelection = (roleTab) => {
    navigate('/login', { state: { preselect: roleTab } });
  };

  return (
    <div className="elegant-home-layout">
      {/* Navigation */}
      <nav className="elegant-nav elegant-nav--light">
        <div className="elegant-nav-brand">
          <img src="/refupass-mark.svg" alt="RefuPass" className="elegant-nav-logo" />
          <span className="elegant-brand-text">RefuPass</span>
        </div>
        <div className="elegant-nav-links">
          {session ? (
            <Link to={dashboardPath} className="button button-primary">Return to Dashboard</Link>
          ) : (
            <Link to="/login" className="button">Sign In <ArrowRight size={16} strokeWidth={1.5} /></Link>
          )}
        </div>
      </nav>

      {/* Hero Section — Split layout */}
      <section className="hero-split">
        <div className="hero-split__image-col">
          <div className="hero-split__image-wrap">
            <img src="/istockphoto-640305394-612x612.jpg" alt="Children smiling" className="hero-split__img" />
            <div className="hero-split__image-accent"></div>
          </div>
          {/* Floating stat badges */}
          <div className="hero-float-badge hero-float-badge--top">
            <ShieldCheck size={18} strokeWidth={2} />
            <span>Identity Verified</span>
          </div>
          <div className="hero-float-badge hero-float-badge--bottom">
            <Heart size={18} strokeWidth={2} />
            <span>30M+ People in Need</span>
          </div>
        </div>

        <div className="hero-split__content-col">
          <p className="eyebrow">Humanitarian Aid Platform</p>
          <h1 className="hero-split__title">Restoring Dignity<br/>Through <span className="hero-split__title-accent">Verification.</span></h1>
          <p className="hero-split__subtitle">
            A secure, unified platform connecting global aid organizations with those who need it most — powered by verifiable credentials.
          </p>

          <div className="hero-split__roles">
            <button onClick={() => handleRoleSelection('aid_worker')} className="hero-role-chip">
              <span className="hero-role-chip__icon"><User size={20} strokeWidth={1.5} /></span>
              <div className="hero-role-chip__text">
                <strong>Aid Worker</strong>
                <span>Field deployment access</span>
              </div>
              <ArrowRight size={16} strokeWidth={1.5} className="hero-role-chip__arrow" />
            </button>
            <button onClick={() => handleRoleSelection('ngo_admin')} className="hero-role-chip">
              <span className="hero-role-chip__icon"><Users size={20} strokeWidth={1.5} /></span>
              <div className="hero-role-chip__text">
                <strong>NGO Administration</strong>
                <span>Camp & resource management</span>
              </div>
              <ArrowRight size={16} strokeWidth={1.5} className="hero-role-chip__arrow" />
            </button>
            <button onClick={() => handleRoleSelection('platform_admin')} className="hero-role-chip">
              <span className="hero-role-chip__icon"><Shield size={20} strokeWidth={1.5} /></span>
              <div className="hero-role-chip__text">
                <strong>Platform Admin</strong>
                <span>Global oversight & control</span>
              </div>
              <ArrowRight size={16} strokeWidth={1.5} className="hero-role-chip__arrow" />
            </button>
          </div>
        </div>
      </section>

      {/* Value Propositions */}
      <section className="value-strip">
        <div className="value-strip__inner">
          <div className="value-strip__item">
            <div className="value-strip__icon"><ShieldCheck size={24} strokeWidth={1.5} /></div>
            <h3>Verified Identity</h3>
            <p>eSignet-powered digital identity verification for every beneficiary in the registry.</p>
          </div>
          <div className="value-strip__item">
            <div className="value-strip__icon"><Fingerprint size={24} strokeWidth={1.5} /></div>
            <h3>Tamper-Proof Passes</h3>
            <p>QR-based verifiable credentials that prevent duplication and ensure fair distribution.</p>
          </div>
          <div className="value-strip__item">
            <div className="value-strip__icon"><Heart size={24} strokeWidth={1.5} /></div>
            <h3>Dignified Access</h3>
            <p>Compassionate logistics that respect privacy while ensuring aid reaches those who need it.</p>
          </div>
        </div>
      </section>

      {/* Feature Section */}
      <section className="elegant-features">
        <div className="elegant-feature-row">
          <div className="elegant-feature-text">
            <p className="eyebrow">How It Works</p>
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
        <div className="elegant-gallery-header">
          <p className="eyebrow">In the Field</p>
          <h2>Impact in Action</h2>
        </div>
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
          <img src="/refupass-mark.svg" alt="RefuPass" style={{height: 28, marginBottom: '1rem', opacity: 0.5}} />
          <p>© 2026 RefuPass Humanitarian Trust. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}
