// AuthPage.jsx — signup and login.
// The right panel drifts real database rows past, so the page demonstrates
// the product's substance before the user has typed anything.

import { useState, useEffect } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "../components/ThemeToggle";

// Straight from bd_foods.json — per 100 g, with the FCT code.
const ROWS = [
  { bn: "ভাত", en: "Rice, boiled", v: "109 kcal", code: "01_0037" },
  { bn: "ইলিশ", en: "Hilsha", v: "18.0 g protein", code: "09_0033" },
  { bn: "মসুর ডাল", en: "Lentil, boiled", v: "13.6 g protein", code: "02_0015" },
  { bn: "রুই", en: "Rohu", v: "20.6 g protein", code: "09_0060" },
  { bn: "পালং শাক", en: "Spinach, boiled", v: "5.3 g fibre", code: "04_0035" },
  { bn: "আম", en: "Mango, Langra", v: "82 kcal", code: "08_0026" },
  { bn: "করলা ভাজি", en: "Bitter gourd, fried", v: "130 kcal", code: "03_0048" },
  { bn: "টুনা", en: "Tuna", v: "25.0 g protein", code: "09_0069" },
  { bn: "মুড়ি", en: "Puffed rice", v: "361 kcal", code: "01_0023" },
  { bn: "কাঁঠাল", en: "Jackfruit", v: "7.2 g fibre", code: "08_0017" },
];

function DataStream() {
  const reduce = useReducedMotion();
  const [top, setTop] = useState(0);

  useEffect(() => {
    if (reduce) return;
    const t = setInterval(() => setTop((n) => (n + 1) % ROWS.length), 2200);
    return () => clearInterval(t);
  }, [reduce]);

  // Six rows visible at a time, cycling
  const visible = Array.from({ length: 6 }, (_, i) => ROWS[(top + i) % ROWS.length]);

  return (
    <div className="relative h-full flex flex-col justify-center overflow-hidden">
      {/* soft edges so rows fade rather than clip */}
      <div className="absolute inset-x-0 top-0 h-24 z-10 pointer-events-none"
           style={{ background: "linear-gradient(var(--surface-2), transparent)" }} />
      <div className="absolute inset-x-0 bottom-0 h-24 z-10 pointer-events-none"
           style={{ background: "linear-gradient(transparent, var(--surface-2))" }} />

      <div className="px-10">
        <p className="mono text-[10px] tracking-[0.22em] uppercase
                      text-[var(--brand)] mb-8">
          <span className="inline-block w-5 h-px bg-[var(--brand)] align-middle mr-3" />
          274 verified foods
        </p>

        <div className="space-y-1">
          <AnimatePresence initial={false} mode="popLayout">
            {visible.map((r, idx) => (
              <motion.div
                key={`${r.code}-${top}`}
                layout
                initial={{ opacity: 0, y: 24 }}
                animate={{
                  opacity: idx === 0 ? 0.35 : idx === 5 ? 0.35 : 1,
                  y: 0,
                }}
                exit={{ opacity: 0, y: -24 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="flex items-baseline gap-4 py-2.5
                           border-b border-[var(--border)]"
              >
                <span className="bn text-[15px] text-[var(--text)] w-24 shrink-0">
                  {r.bn}
                </span>
                <span className="text-[13px] text-[var(--text-dim)] flex-1 truncate">
                  {r.en}
                </span>
                <span className="tnum text-[13px] font-medium text-[var(--brand)]
                                 shrink-0">
                  {r.v}
                </span>
                <span className="mono text-[9.5px] text-[var(--text-faint)]
                                 w-16 text-right shrink-0">
                  {r.code}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        <p className="mt-8 text-[12px] text-[var(--text-faint)] leading-relaxed max-w-sm">
          Every figure traces to a row in the Food Composition Table for
          Bangladesh. Nothing is estimated.
        </p>
      </div>
    </div>
  );
}

export default function AuthPage({ mode = "login" }) {
  const isSignup = mode === "signup";
  const navigate = useNavigate();
  const auth = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit() {
    if (busy) return;
    setError(null);

    if (isSignup && password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setBusy(true);
    try {
      const data = isSignup
        ? await auth.signup(email, password)
        : await auth.login(email, password);

      // New users need a profile before answers can be personalised.
      navigate(data.has_profile ? "/chat" : "/setup");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const inputCls =
    "w-full px-3.5 py-2.5 rounded-lg bg-[var(--surface)] " +
    "border border-[var(--border-strong)] text-[15px] text-[var(--text)] " +
    "outline-none focus:border-[var(--brand)] transition-colors";

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[var(--bg)]">

      {/* form */}
      <div className="flex items-center justify-center px-6 py-12 relative">
        <div className="absolute top-5 right-5"><ThemeToggle /></div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm"
        >
          <button onClick={() => navigate("/")}
                  className="mb-10 flex items-baseline gap-2">
            <span className="display text-xl font-semibold text-[var(--text)]">
              NutriBot
            </span>
            <span className="mono text-[10px] tracking-[0.18em] text-[var(--brand)]">
              BD
            </span>
          </button>

          <AnimatePresence mode="wait">
            <motion.div key={mode}
              initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }} transition={{ duration: 0.25 }}>
              <h1 className="display text-[1.9rem] font-semibold text-[var(--text)] mb-2">
                {isSignup ? "Create an account" : "Welcome back"}
              </h1>
              <p className="text-[14px] text-[var(--text-dim)] mb-8">
                {isSignup
                  ? "Your profile makes every answer specific to you."
                  : "Sign in to pick up where you left off."}
              </p>
            </motion.div>
          </AnimatePresence>

          <div className="space-y-3">
            <label className="block">
              <span className="block text-[11px] text-[var(--text-dim)] mb-1.5">Email</span>
              <input type="email" value={email} autoComplete="email"
                     onChange={(e) => setEmail(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                     className={inputCls} />
            </label>

            <label className="block">
              <span className="block text-[11px] text-[var(--text-dim)] mb-1.5">
                Password{isSignup && " (8 characters or more)"}
              </span>
              <input type="password" value={password}
                     autoComplete={isSignup ? "new-password" : "current-password"}
                     onChange={(e) => setPassword(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                     className={inputCls} />
            </label>
          </div>

          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-3 text-[13px] text-[var(--danger)]"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>

          <motion.button
            onClick={handleSubmit}
            disabled={busy || !email || !password}
            whileTap={{ scale: 0.98 }}
            className="w-full mt-6 py-3 rounded-full bg-[var(--brand)]
                       text-[var(--brand-text)] text-[15px] font-medium
                       transition-opacity hover:opacity-90 disabled:opacity-30"
          >
            {busy ? "…" : isSignup ? "Create account" : "Sign in"}
          </motion.button>

          <p className="mt-5 text-center text-[13px] text-[var(--text-dim)]">
            {isSignup ? "Already have an account?" : "No account yet?"}{" "}
            <button onClick={() => navigate(isSignup ? "/login" : "/signup")}
                    className="text-[var(--brand)] font-medium hover:underline">
              {isSignup ? "Sign in" : "Create one"}
            </button>
          </p>

          <p className="mt-8 text-center text-[12px] text-[var(--text-faint)]">
            Or{" "}
            <button onClick={() => navigate("/chat")}
                    className="underline hover:text-[var(--brand)] transition-colors">
              try it without an account
            </button>
          </p>
        </motion.div>
      </div>

      {/* data panel — hidden on small screens, where it would just be noise */}
      <div className="hidden lg:block bg-[var(--surface-2)]
                      border-l border-[var(--border)]">
        <DataStream />
      </div>
    </div>
  );
}