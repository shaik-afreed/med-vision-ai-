import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { warmUpModel } from "../api/api";
import { initialsOf, useAuth } from "../context/AuthContext";
import Icon from "./Icon";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", short: "Home", icon: "home", end: true },
  { to: "/patients", label: "Patients", short: "Patients", icon: "users" },
  { to: "/xray", label: "X-Ray Analysis", short: "X-Ray", icon: "scan" },
  { to: "/documents", label: "Report Analysis", short: "Lab", icon: "fileText" },
  { to: "/reports", label: "Medical Reports", short: "Reports", icon: "folder" },
];

function BrandMark({ size = 40 }) {
  return (
    <div className="brand-icon" style={{ width: size, height: size }}>
      <Icon name="activity" size={Math.round(size * 0.55)} strokeWidth={2.2} />
    </div>
  );
}

function Sidebar({ open, onClose }) {
  const { logout, user } = useAuth();

  return (
    <aside id="app-sidebar" className={`sidebar ${open ? "open" : ""}`}>
      <div className="brand">
        <BrandMark />
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
          <Icon name="x" size={22} />
        </button>
      </div>

      <nav className="navigation" aria-label="Main">
        <span className="nav-section">Workspace</span>

        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onClose}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <Icon name={item.icon} size={19} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-note">
          <Icon name="shield" size={16} />
          <span>Screening aid only. Every result needs clinician review.</span>
        </div>

        <div className="user-card">
          <div className="avatar">{initialsOf(user?.name)}</div>
          <div className="user-card-text">
            <strong>{user?.name || "Doctor"}</strong>
            <span>{user?.email || "Medical staff"}</span>
          </div>
        </div>

        <button
          className="nav-item sign-out"
          onClick={() => {
            onClose();
            logout();
          }}
          type="button"
        >
          <Icon name="logOut" size={19} />
          <span>Sign Out</span>
        </button>
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

  // Start loading the AI model server-side while the user is on the
  // dashboard, so their first X-ray analysis doesn't wait for it.
  useEffect(() => {
    warmUpModel().catch(() => {});
  }, []);

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
          <Icon name="menu" size={22} />
        </button>
        <BrandMark size={32} />
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

      {/* Thumb-reach navigation, phones only (hidden by CSS elsewhere). */}
      <nav className="bottom-nav" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            aria-label={item.label}
            className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}
          >
            <Icon name={item.icon} size={22} />
            <span aria-hidden="true">{item.short}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
