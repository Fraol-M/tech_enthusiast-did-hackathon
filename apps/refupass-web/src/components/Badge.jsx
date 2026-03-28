export default function Badge({ tone = "neutral", className = "", children }) {
  const classes = ["badge", `badge-${tone}`, className].filter(Boolean).join(" ");
  return <span className={classes}>{children}</span>;
}
