import { NavLink } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import Button from "./Button";

export default function Shell({ session, onLogout, title, subtitle, navItems, children, aside }) {
  const ngoName = session?.ngoName || "RefuPass NGO";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark-wrap">
            <img src="/refupass-mark.svg" alt="RefuPass" className="brand-mark" />
          </div>
          <div className="brand-copy">
            <p className="eyebrow">Operations</p>
            <h1>RefuPass</h1>
            <p className="brand-subtitle">Food aid control</p>
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              <span className="nav-link-label">
                {item.icon ? <item.icon size={16} strokeWidth={2.2} /> : null}
                <span>{item.label}</span>
              </span>
              {item.meta && <small>{item.meta}</small>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-summary">
            <div className="user-chip">
              <ShieldCheck size={14} strokeWidth={2.2} />
              <span>{session.displayName}</span>
            </div>
            <div className="user-chip user-chip-muted">
              <span>{ngoName}</span>
            </div>
            <p className="eyebrow">Role: {session.role.replace("_", " ")}</p>
          </div>
          <Button className="full-width" variant="secondary" type="button" onClick={onLogout}>
            Sign out
          </Button>
        </div>
      </aside>
      <main className="main-panel">
        <header className="page-header">
          <div>
            <p className="eyebrow">RefuPass</p>
            <h2>{title}</h2>
            {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
          </div>
          <div className="header-aside">
            <div className="header-kicker">{session.role === "aid_worker" ? "Field verification" : "Administration"}</div>
            {aside}
          </div>
        </header>
        <section className="page-content">{children}</section>
      </main>
    </div>
  );
}
