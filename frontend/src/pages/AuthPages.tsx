import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Logo, ThemeToggle } from "../components/Layout";
import { ErrorState } from "../components/ui";
import { useAuth } from "../hooks/useAuth";

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-4">
      <div className="absolute right-4 top-4"><ThemeToggle /></div>
      <Logo />
      <div className="card w-full max-w-sm">
        <h1 className="mb-4 text-xl font-bold">{title}</h1>
        {children}
      </div>
      <Link to="/" className="text-sm text-slate-500 hover:underline dark:text-slate-400">← Back to home</Link>
    </div>
  );
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await login(email, password);
      navigate((location.state as { from?: string } | null)?.from ?? "/dashboard", { replace: true });
    } catch (err) { setError(err instanceof Error ? err.message : "Login failed."); } finally { setBusy(false); }
  }

  return (
    <Shell title="Log in">
      <form onSubmit={submit} className="space-y-3">
        <div><label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div><label className="label" htmlFor="password">Password</label>
          <input id="password" type="password" required autoComplete="current-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        {error && <ErrorState message={error} />}
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Signing in…" : "Log in"}</button>
        <p className="text-center text-sm text-slate-500">No account? <Link className="font-medium text-heat-orange hover:underline" to="/signup">Sign up</Link></p>
      </form>
    </Shell>
  );
}

export function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await signup(email, password, name || undefined); navigate("/profile", { replace: true }); }
    catch (err) { setError(err instanceof Error ? err.message : "Sign-up failed."); } finally { setBusy(false); }
  }

  return (
    <Shell title="Create your account">
      <form onSubmit={submit} className="space-y-3">
        <div><label className="label" htmlFor="name">Name (optional)</label>
          <input id="name" className="input" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} /></div>
        <div><label className="label" htmlFor="su-email">Email</label>
          <input id="su-email" type="email" required autoComplete="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div><label className="label" htmlFor="su-password">Password (min. 8 characters)</label>
          <input id="su-password" type="password" required minLength={8} autoComplete="new-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        {error && <ErrorState message={error} />}
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Creating…" : "Sign up"}</button>
        <p className="text-center text-sm text-slate-500">Already registered? <Link className="font-medium text-heat-orange hover:underline" to="/login">Log in</Link></p>
      </form>
    </Shell>
  );
}
