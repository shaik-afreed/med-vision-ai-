import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "⌂", end: true },
  { to: "/patients", label: "Patients", icon: "♙" },
  { to: "/xray", label: "X-Ray Analysis", icon: "▣" },
  { to: "/documents", label: "Report Analysis", icon: "📄" },
  { to: "/reports", label: "Medical Reports", icon: "▤" },
];

function Sidebar() {
  const { logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">M</div>
        <div>
          <h1>MediVision</h1>
          <span>AI Healthcare</span>
        </div>
      </div>

      <nav className="navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `nav-item ${isActive ? "active" : ""}`
            }
          >
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}

        <button className="nav-item" onClick={logout} type="button">
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
  return (
    <div className="app">
      <Sidebar />
      <main className="main-content">
        <div className="main-inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
