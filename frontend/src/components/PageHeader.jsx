/**
 * One consistent page header for every screen: title + subtitle on the
 * left, optional actions/status on the right.
 */
export default function PageHeader({ title, subtitle, children }) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </header>
  );
}
