export default function StatCard({ label, value, hint, icon: Icon }) {
  return (
    <article className="stat-card">
      <div className="stat-card-top">
        <div>
          <p className="eyebrow">{label}</p>
          <strong>{value}</strong>
        </div>
        {Icon ? (
          <span className="stat-icon">
            <Icon size={18} strokeWidth={2.2} />
          </span>
        ) : null}
      </div>
      {hint ? <span className="stat-hint">{hint}</span> : null}
    </article>
  );
}
