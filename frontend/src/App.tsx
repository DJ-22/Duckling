import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";
import { getMe, type Me } from "./lib/api";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  if (loading) {
    return <Centered>Loading…</Centered>;
  }

  return (
    <Centered>
      {session ? <RoundTrip onSignOut={() => supabase.auth.signOut()} /> : <Login />}
    </Centered>
  );
}

function Login() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");

  async function sendLink(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setError("");
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) {
      setError(error.message);
      setStatus("error");
    } else {
      setStatus("sent");
    }
  }

  return (
    <div className="w-full max-w-sm space-y-4">
      <h1 className="text-2xl font-semibold">Duckling</h1>
      {status === "sent" ? (
        <p className="text-sm text-gray-600">
          Check <span className="font-medium">{email}</span> for a magic link, then return here.
        </p>
      ) : (
        <form onSubmit={sendLink} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
          <button
            type="submit"
            disabled={status === "sending"}
            className="w-full rounded bg-black px-3 py-2 text-white disabled:opacity-50"
          >
            {status === "sending" ? "Sending…" : "Send magic link"}
          </button>
          {status === "error" && <p className="text-sm text-red-600">{error}</p>}
        </form>
      )}
    </div>
  );
}

function RoundTrip({ onSignOut }: { onSignOut: () => void }) {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState("");

  async function callMe() {
    setError("");
    setMe(null);
    try {
      setMe(await getMe());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  }

  return (
    <div className="w-full max-w-sm space-y-4">
      <h1 className="text-2xl font-semibold">Signed in</h1>
      <button onClick={callMe} className="w-full rounded bg-black px-3 py-2 text-white">
        Call GET /api/me
      </button>
      {me && (
        <pre className="overflow-x-auto rounded bg-gray-100 p-3 text-sm">
          {JSON.stringify(me, null, 2)}
        </pre>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button onClick={onSignOut} className="text-sm text-gray-500 underline">
        Sign out
      </button>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white p-6 text-gray-900">
      {children}
    </div>
  );
}
