import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "⌂", end: true },
  { to: "/patients", label: "Patients", icon: "♙" },
  { to: "/xray", label: "X-Ray Analysis", icon: "▣" },
  { to: "/documents", label: "Report Analysis", icon: "📄" },
  { to: "/reports", label: "Medical Reports", icon: "▤" },
];

function Sidebar({ open, onClose }) {
  const { logout } = useAuth();

  return (
    <aside id="app-sidebar" className={`sidebar ${open ? "open" : ""}`}>
      <div className="brand">
        <div className="brand-icon">M</div>
        <div>
          <h1>MediVision</h1>
          <span>AI Healthcare</span>
        </div>
        <button
          type="button"
          className="sidebar-close"
          onClick={onClose}
          aria-label="Close navigation menu"
        >
          ×
        </button>
      </div>

      <nav className="navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onClose}
            className={({ isActive }) =>
              `nav-item ${isActive ? "active" : ""}`
            }
          >
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}

        <button
          className="nav-item"
          onClick={() => {
            onClose();
            logout();
          }}
          type="button"
        >
          <span>⏻</span>
          Sign Out
        </button>
      </nav>

      <div className="sidebar-bottom">
        <div className="user-card">
          <div className="avatar">DR</div>
          <div>
            <strong>Doctor</strong>
            <span>Medical Staff</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default function Layout() {
  // Only has a visible effect on small screens, where the sidebar becomes
  // a slide-in drawer opened from the mobile top bar (see App.css).
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return undefined;

    function handleKeyDown(event) {
      if (event.key === "Escape") setMenuOpen(false);
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [menuOpen]);

  return (
    <div className="app">
      <header className="mobile-topbar">
        <button
          type="button"
          className="menu-toggle"
          onClick={() => setMenuOpen(true)}
          aria-label="Open navigation menu"
          aria-expanded={menuOpen}
          aria-controls="app-sidebar"
        >
          ☰
        </button>
        <div className="brand-icon">M</div>
        <strong>MediVision</strong>
      </header>

      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />

      {menuOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      <main className="main-content">
        <div className="main-inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
