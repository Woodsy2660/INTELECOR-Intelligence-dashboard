import { NavLink, Outlet, useLocation } from "react-router-dom";

const navItems = [
  { to: "/overview",    label: "Overview",    icon: "dashboard" },
  { to: "/financial",   label: "Financial",   icon: "payments" },
  { to: "/operations",  label: "Operations",  icon: "settings_accessibility" },
  { to: "/documents",   label: "Documents",   icon: "description" },
  { to: "/settings",    label: "Settings",    icon: "settings" },
];

const pageTitles: Record<string, string> = {
  "/overview":   "Overview",
  "/financial":  "Financial",
  "/operations": "Operations",
  "/documents":  "Documents",
  "/settings":   "Settings",
};

export default function Layout() {
  const { pathname } = useLocation();
  const title = pageTitles[pathname] ?? "Overview";

  return (
    <div className="flex min-h-screen overflow-hidden" style={{ backgroundColor: "#e8eaf0" }}>
      {/* ── Sidebar ── */}
      <aside
        className="hidden md:flex flex-col h-screen w-64 p-6 space-y-4 sticky top-0 z-20"
        style={{
          backgroundColor: "#e8eaf0",
          boxShadow: "6px 0 12px rgba(0,0,0,0.08)",
          borderRadius: "0 1rem 1rem 0",
        }}
      >
        <div className="mb-8 px-2">
          <span className="text-xl font-semibold tracking-tight" style={{ color: "#6366f1" }}>
            INTELECOR
          </span>
        </div>

        <nav className="flex-1 space-y-2">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "neomorph-inset font-semibold"
                    : "text-slate-500 hover:text-slate-700"
                }`
              }
              style={({ isActive }) =>
                isActive ? { color: "#6366f1" } : {}
              }
            >
              <span className="material-symbols-outlined text-[20px]">{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
        {/* Top bar */}
        <header
          className="flex items-center justify-between px-8 w-full h-20 sticky top-0 z-10"
          style={{
            backgroundColor: "#e8eaf0",
            boxShadow: "0 4px 12px rgba(0,0,0,0.03)",
          }}
        >
          <h1 className="font-semibold text-lg" style={{ color: "#2e3040" }}>{title}</h1>

          <div className="flex items-center gap-4">
            <button
              className="neomorph-raised p-2 rounded-full text-slate-500 hover:text-indigo-500 transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">calendar_today</span>
            </button>
            <div className="relative">
              <button
                className="neomorph-raised p-2 rounded-full text-slate-500 hover:text-indigo-500 transition-colors"
              >
                <span className="material-symbols-outlined text-[20px]">notifications</span>
              </button>
              <span
                className="absolute top-1 right-1 w-2.5 h-2.5 rounded-full border-2"
                style={{ backgroundColor: "#6366f1", borderColor: "#e8eaf0" }}
              />
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1">
          <Outlet />
        </main>
      </div>

      {/* ── Mobile bottom nav ── */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 h-16 flex items-center justify-around z-30"
        style={{ backgroundColor: "#e8eaf0", boxShadow: "0 -4px 12px rgba(0,0,0,0.05)" }}
      >
        {navItems.slice(0, 4).map(({ to, label, icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) =>
            `flex flex-col items-center text-[10px] ${isActive ? "font-bold" : ""}`
          }
          style={({ isActive }) => ({ color: isActive ? "#6366f1" : "#94a3b8" })}
          >
            <span className="material-symbols-outlined text-[22px]">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
