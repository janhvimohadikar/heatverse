import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";

const NAV = [
  { to: "/dashboard", label: "Dashboard", auth: true },
  { to: "/map", label: "Heat-Risk Map" },
  { to: "/trends", label: "Climate Trends" },
  { to: "/predictions", label: "Predictions", auth: true },
  { to: "/safety", label: "Safety & Emergency" },
  { to: "/profile", label: "My Profile", auth: true },
  { to: "/admin", label: "Admin", admin: true },
];

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2" aria-label="HEATVERSE home">
      <span className="flex h-8 w-8 items-center justify-center rounded-md bg-navy-900 text-lg font-bold text-heat-orange dark:bg-navy-700">H</span>
      <span className="leading-tight">
        <span className="block text-sm font-bold tracking-wide text-navy-900 dark:text-white">HEATVERSE</span>
        <span className="block text-[10px] uppercase tracking-widest text-slate-500 dark:text-slate-400">Heat intelligence</span>
      </span>
    </Link>
  );
}

export function ThemeToggle() {
  const { toggle } = useTheme();
  return (
    <button className="btn-secondary" onClick={toggle} aria-label="Toggle light and dark mode" title="Toggle light / dark mode">
      <span className="dark:hidden">☾ Dark</span>
      <span className="hidden dark:inline">☀ Light</span>
    </button>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const items = NAV.filter((n) => (!n.auth || user) && (!n.admin || user?.role === "admin"));

  const links = (
    <nav className="flex flex-col gap-1" aria-label="Main">
      {items.map((n) => (
        <NavLink key={n.to} to={n.to} onClick={() => setOpen(false)}
          className={({ isActive }) => `rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-navy-900 text-white dark:bg-heat-orange" : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-navy-800"}`}>
          {n.label}
        </NavLink>
      ))}
    </nav>
  );

  const footer = (
    <div className="mt-auto space-y-2 border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-navy-700 dark:text-slate-400">
      <p>Data: India daily weather 2000–2024 (supplied dataset)</p>
      {user ? (
        <button className="btn-secondary w-full" onClick={() => { logout(); navigate("/"); }}>Log out</button>
      ) : (
        <Link to="/login" className="btn-primary w-full">Log in</Link>
      )}
    </div>
  );

  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-60 shrink-0 flex-col gap-6 border-r border-slate-200 bg-white p-4 dark:border-navy-700 dark:bg-navy-900 lg:sticky lg:top-0 lg:flex lg:h-screen">
        <Logo />
        {links}
        {footer}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-slate-200 bg-white/95 px-4 py-2.5 dark:border-navy-700 dark:bg-navy-900/95 lg:static">
          <div className="flex items-center gap-2 lg:hidden">
            <button className="btn-secondary" aria-label="Open menu" aria-expanded={open} onClick={() => setOpen(true)}>☰</button>
            <Logo />
          </div>
          <p className="hidden text-sm text-slate-500 dark:text-slate-400 lg:block">Climate &amp; health</p>
          <div className="flex items-center gap-2">
            {user && <span className="hidden text-sm text-slate-600 dark:text-slate-300 sm:inline">{user.email}</span>}
            <ThemeToggle />
          </div>
        </header>

        {open && (
          <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
            <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
            <div className="absolute left-0 top-0 flex h-full w-64 flex-col gap-6 bg-white p-4 dark:bg-navy-900">
              <div className="flex items-center justify-between">
                <Logo />
                <button className="btn-secondary" aria-label="Close menu" onClick={() => setOpen(false)}>✕</button>
              </div>
              {links}
              {footer}
            </div>
          </div>
        )}

        <main className="flex-1 p-4 sm:p-6"><Outlet /></main>
      </div>
    </div>
  );
}
