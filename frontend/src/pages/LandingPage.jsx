// LandingPage.jsx — the public front door.
// The hero doesn't describe the product, it performs it: the same question
// answered twice, side by side, so the difference is watched rather than read.

import { useState, useEffect, useRef } from "react";
import { motion, useReducedMotion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import CalorieCalculator from "../components/CalorieCalculator";
import ThemeToggle from "../components/ThemeToggle";

// Real rows from the database. The numbers must be the ones the system
// actually returns, or the hero is a lie.
const RACES = [
  {
    q: "এক প্লেট ভাতে কত ক্যালরি?",
    roman: "ek plate bhat e koto calorie?",
    vague: "Around 200–300 calories, depending on the serving.",
    exact: "272 kcal per plate (250 g)",
    code: "INFS FCT 01_0037",
  },
  {
    q: "ইলিশে কত প্রোটিন?",
    roman: "ilish e koto protein?",
    vague: "Roughly 22 g of protein per 100 g of hilsa.",
    exact: "18.0 g protein per 100 g · 13.5 g per piece",
    code: "INFS FCT 09_0033",
  },
  {
    q: "ডিমে কত প্রোটিন?",
    roman: "dim e koto protein?",
    vague: "About 6 g of protein in one large egg.",
    exact: "Not in the database yet — I won't guess.",
    code: null,
  },
];

const FACTS = [
  { n: "274", label: "foods from the national table", sub: "six food groups, complete" },
  { n: "3", label: "ways to ask", sub: "বাংলা · English · Banglish" },
  { n: "0", label: "invented numbers", sub: "every value carries its table code" },
];

const STEPS = [
  { k: "01", t: "Your question", d: "Typed however you type — Bangla script, English, or romanised." },
  { k: "02", t: "Routed", d: "A fine-tuned classifier decides what kind of question this is." },
  { k: "03", t: "Looked up", d: "Keyword and meaning-based search find the matching rows." },
  { k: "04", t: "Answered", d: "Written in your language, citing the row it came from." },
];

const LIMITS = [
  "No eggs, milk, or meat yet — those pages of the table aren't transcribed.",
  "No restaurant dishes. Biriyani and tehari aren't in the national table.",
  "Portion weights are our assumption; the per-100 g values are the verified ones.",
  "Bangla script retrieves less reliably than romanised input. We measured it.",
  "Information, not medical advice. Talk to a doctor about your condition.",
];

/** Types a string out, character by character. */
function useTypewriter(text, speed, startDelay, active) {
  const [shown, setShown] = useState("");

  useEffect(() => {
    if (!active) { setShown(text); return; }
    setShown("");
    let i = 0;
    const start = setTimeout(() => {
      const timer = setInterval(() => {
        i += 1;
        setShown(text.slice(0, i));
        if (i >= text.length) clearInterval(timer);
      }, speed);
    }, startDelay);
    return () => clearTimeout(start);
  }, [text, speed, startDelay, active]);

  return shown;
}

function AnswerCard({ label, text, speed, delay, active, grounded, code, done }) {
  const typed = useTypewriter(text, speed, delay, active);

  return (
    <div
      className={`rounded-2xl p-6 min-h-[190px] flex flex-col ${
        grounded
          ? "bg-[var(--surface-3)] border border-[var(--brand)]/60 shadow-[0_2px_32px_-12px_var(--brand)]"
          : "bg-[var(--surface)] border border-[var(--border)]"
      }`}
    >
      <div className={`mono text-[9.5px] tracking-[0.18em] uppercase mb-4 ${
        grounded ? "text-[var(--brand)]" : "text-[var(--text-faint)]"}`}>
        {label}
      </div>

      <p className={`flex-1 text-[15px] leading-[1.6] ${
        grounded ? "text-[var(--text)] font-medium tnum" : "text-[var(--text-dim)]"}`}>
        {typed}
        {active && typed.length < text.length && (
          <span className="inline-block w-[2px] h-[1em] ml-0.5 align-middle
                           bg-[var(--text-dim)] animate-pulse" />
        )}
      </p>

      <div className={`mt-5 pt-4 border-t ${
        grounded ? "border-[var(--brand)]/20" : "border-dashed border-[var(--border)]"}`}>
        {grounded ? (
          <AnimatePresence>
            {done && (
              code ? (
                <motion.span
                  initial={{ opacity: 0, scale: 0.85, y: 4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ type: "spring", stiffness: 340, damping: 20 }}
                  className="mono inline-block text-[10.5px] px-2.5 py-1 rounded-full
                             bg-[var(--surface)] border border-[var(--brand)]/30
                             text-[var(--brand)]"
                >
                  {code}
                </motion.span>
              ) : (
                <motion.span
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="mono text-[10.5px] text-[var(--brand)]"
                >
                  refused — nothing to cite
                </motion.span>
              )
            )}
          </AnimatePresence>
        ) : (
          <span className="mono text-[10.5px] text-[var(--danger)]">no source</span>
        )}
      </div>
    </div>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const heroRef = useRef(null);

  const [i, setI] = useState(0);
  const [phase, setPhase] = useState("typing");   // typing -> done
  const [scrolled, setScrolled] = useState(false);

  const race = RACES[i];

  // One cycle: question types, both answers race, citation lands, hold, next.
  useEffect(() => {
    if (reduce) return;
    setPhase("typing");
    const settle = setTimeout(() => setPhase("done"), 3200);
    const next = setTimeout(() => setI((n) => (n + 1) % RACES.length), 7000);
    return () => { clearTimeout(settle); clearTimeout(next); };
  }, [i, reduce]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : -40]);

  const rise = {
    hidden: { opacity: 0, y: reduce ? 0 : 18 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
  };

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]
                    selection:bg-[var(--brand)] selection:text-[var(--brand-text)]">

      {/* nav */}
      <nav className={`sticky top-0 z-50 backdrop-blur-md transition-all duration-300
                       ${scrolled
                         ? "bg-[var(--bg)]/90 border-b border-[var(--border)]"
                         : "bg-transparent border-b border-transparent"}`}>
        <div className="max-w-6xl mx-auto px-6 h-[70px] flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="display text-[21px] font-semibold">NutriBot</span>
            <span className="mono text-[10px] tracking-[0.18em] text-[var(--brand)]">BD</span>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button
              onClick={() => navigate("/login")}
              className="px-3 py-2 text-[13px] text-[var(--text-dim)]
                         hover:text-[var(--text)] transition-colors"
            >
              Sign in
            </button>
            <button
              onClick={() => navigate("/signup")}
              className="group px-5 py-2 rounded-full bg-[var(--brand)]
                         text-[var(--brand-text)] text-[13px] font-medium
                         transition-all hover:opacity-90 active:scale-[0.97]"
            >
              Get started
              <span className="inline-block ml-1.5 transition-transform
                               group-hover:translate-x-0.5">→</span>
            </button>
          </div>
        </div>
      </nav>

      {/* hero */}
      <header ref={heroRef} className="max-w-6xl mx-auto px-6 pt-14 pb-24 md:pt-20">
        <motion.div style={{ y: heroY }}>
          <motion.div initial="hidden" animate="show"
                      variants={{ show: { transition: { staggerChildren: 0.09 } } }}>

            <motion.p variants={rise}
                      className="mono text-[10px] tracking-[0.22em] uppercase
                                 text-[var(--brand)] mb-6">
              <span className="inline-block w-6 h-px bg-[var(--brand)] align-middle mr-3" />
              Food Composition Table for Bangladesh · INFS, University of Dhaka
            </motion.p>

            <motion.h1 variants={rise}
                       className="display font-semibold max-w-[19ch] md:max-w-[24ch]"
                       style={{ fontSize: "clamp(2.4rem, 6.2vw, 4.4rem)", lineHeight: 1.04 }}>
              Most nutrition tools guess at
              <span className="bn text-[var(--brand)] font-medium"> ভাত</span>,
              <span className="bn text-[var(--brand)] font-medium"> ইলিশ</span> and
              <span className="bn text-[var(--brand)] font-medium"> শাক</span>.
              <br /> This one looks them up.
            </motion.h1>

            <motion.p variants={rise}
                      className="mt-7 text-[17px] md:text-xl text-[var(--text-dim)]
                                 max-w-[52ch] leading-[1.65]">
              Ask in Bangla, English, or the way you actually type. Every answer
              comes from the national food composition table — with the row it
              came from.
            </motion.p>

            {/* the race */}
            <motion.div variants={rise} className="mt-14">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-5">
                <AnimatePresence mode="wait">
                  <motion.span key={`q${i}`}
                    initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.3 }}
                    className="bn text-lg md:text-xl font-semibold">
                    {race.q}
                  </motion.span>
                </AnimatePresence>
                <span className="mono text-[11px] text-[var(--text-faint)]">
                  {race.roman}
                </span>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <AnswerCard
                  key={`v${i}`}
                  label="A general chatbot"
                  text={race.vague}
                  speed={14}
                  delay={300}
                  active={!reduce}
                  grounded={false}
                  done={phase === "done"}
                />
                <AnswerCard
                  key={`e${i}`}
                  label="NutriBot BD"
                  text={race.exact}
                  speed={22}
                  delay={900}
                  active={!reduce}
                  grounded
                  code={race.code}
                  done={phase === "done"}
                />
              </div>

              {/* progress dots — the bar fills over the cycle, so the change
                  reads as timed rather than random */}
              <div className="flex gap-2 mt-6">
                {RACES.map((_, n) => (
                  <button key={n} onClick={() => setI(n)}
                    aria-label={`Example ${n + 1}`}
                    className={`h-[3px] rounded-full overflow-hidden transition-all duration-500
                                ${n === i ? "w-12" : "w-4 hover:opacity-70"}`}
                    style={{ background: "var(--border-strong)" }}>
                    {n === i && !reduce && (
                      <motion.span key={`bar${i}`} className="block h-full"
                        style={{ background: "var(--brand)" }}
                        initial={{ width: "0%" }} animate={{ width: "100%" }}
                        transition={{ duration: 7, ease: "linear" }} />
                    )}
                  </button>
                ))}
              </div>
            </motion.div>

            <motion.div variants={rise} className="mt-12 flex flex-wrap items-center gap-5">
              <button
                onClick={() => navigate("/signup")}
                className="group px-7 py-3.5 rounded-full bg-[var(--brand)]
                           text-[var(--brand-text)] font-medium transition-all
                           hover:opacity-90 active:scale-[0.98]"
              >
                Ask about a food
                <span className="inline-block ml-2 transition-transform
                                 group-hover:translate-x-1">→</span>
              </button>
              <button
                onClick={() => navigate("/chat")}
                className="text-[13px] text-[var(--text-dim)] underline
                           hover:text-[var(--brand)] transition-colors"
              >
                or try it without an account
              </button>
            </motion.div>
          </motion.div>
        </motion.div>
      </header>

      {/* facts */}
      <section className="border-y border-[var(--border)] bg-[var(--surface-2)]">
        <div className="max-w-6xl mx-auto px-6 py-16 grid sm:grid-cols-3 gap-12">
          {FACTS.map((f, n) => (
            <motion.div key={f.label}
              initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.55, delay: n * 0.08, ease: [0.16, 1, 0.3, 1] }}>
              <div className="display tnum text-[3.4rem] font-semibold
                              text-[var(--brand)] leading-[0.9]">{f.n}</div>
              <div className="mt-4 font-medium text-[15px]">{f.label}</div>
              <div className="mt-1.5 text-[13px] text-[var(--text-dim)]">{f.sub}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* calculator */}
      <section className="max-w-5xl mx-auto px-6 py-24">
        <motion.div initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-100px" }}
                    transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}>
          <p className="mono text-[10px] tracking-[0.22em] uppercase text-[var(--brand)] mb-5">
            <span className="inline-block w-6 h-px bg-[var(--brand)] align-middle mr-3" />
            Try it without signing up
          </p>
          <h2 className="display text-[2rem] md:text-[2.7rem] font-semibold mb-4 max-w-[20ch]">
            Start with your own numbers
          </h2>
          <p className="text-[var(--text-dim)] mb-11 max-w-[48ch] leading-relaxed">
            Every answer the chatbot gives is measured against these. Change one
            value and watch the whole picture move.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-60px" }}
                    transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}>
          <CalorieCalculator />
        </motion.div>
      </section>

      {/* how */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <h2 className="display text-[2rem] md:text-[2.7rem] font-semibold mb-4 max-w-[20ch]">
          What happens to your question
        </h2>
        <p className="text-[var(--text-dim)] mb-14 max-w-[48ch] leading-relaxed">
          Four steps. The written answer comes last, and only from what was found.
        </p>

        <div className="grid md:grid-cols-4 gap-x-8 gap-y-10">
          {STEPS.map((s, n) => (
            <motion.div key={s.k}
              initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: n * 0.08, ease: [0.16, 1, 0.3, 1] }}>
              <div className="h-[2px] w-full bg-[var(--accent)] mb-5" />
              <div className="mono text-[10px] tracking-[0.18em]
                              text-[var(--accent)] mb-2.5">{s.k}</div>
              <div className="font-semibold text-[15px] mb-2">{s.t}</div>
              <p className="text-[13.5px] text-[var(--text-dim)] leading-[1.65]">{s.d}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* limits */}
      <section className="bg-[var(--text)] text-[var(--bg)] relative overflow-hidden">
        <div className="absolute inset-0 opacity-40 pointer-events-none"
             style={{ background: "radial-gradient(900px 380px at 18% 0%, var(--brand), transparent 70%)" }} />
        <div className="relative max-w-6xl mx-auto px-6 py-24">
          <h2 className="display text-[2rem] md:text-[2.7rem] font-semibold mb-4 max-w-[16ch]">
            What it won't do
          </h2>
          <p className="opacity-60 mb-12 max-w-[46ch] leading-relaxed">
            A tool that hides its limits is asking you to trust it blindly.
          </p>

          <ul className="grid md:grid-cols-2 gap-x-14 gap-y-6 max-w-4xl">
            {LIMITS.map((l, n) => (
              <motion.li key={l}
                initial={{ opacity: 0, x: -10 }} whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }} transition={{ duration: 0.45, delay: n * 0.06 }}
                className="flex gap-3.5 text-[15px] leading-[1.65]">
                <span className="text-[var(--accent)] mt-[2px] shrink-0" aria-hidden>—</span>
                <span className="opacity-85">{l}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      </section>

      {/* cta */}
      <section className="max-w-6xl mx-auto px-6 py-28 text-center">
        <motion.h2 initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }}
                   viewport={{ once: true, margin: "-80px" }} transition={{ duration: 0.6 }}
                   className="display font-semibold max-w-[18ch] mx-auto"
                   style={{ fontSize: "clamp(2rem, 4.6vw, 3.2rem)", lineHeight: 1.08 }}>
          Ask it something you'd actually eat today.
        </motion.h2>
        <motion.button
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.15 }}
          onClick={() => navigate("/signup")}
          className="group mt-10 px-8 py-4 rounded-full bg-[var(--brand)]
                     text-[var(--brand-text)] font-medium transition-all
                     hover:opacity-90 active:scale-[0.98]"
        >
          Start asking
          <span className="inline-block ml-2 transition-transform
                           group-hover:translate-x-1">→</span>
        </motion.button>
      </section>

      <footer className="border-t border-[var(--border)]">
        <div className="max-w-6xl mx-auto px-6 py-12 flex flex-col sm:flex-row
                        sm:items-start sm:justify-between gap-6">
          <p className="mono text-[10.5px] text-[var(--text-faint)]
                        max-w-[54ch] leading-[1.7]">
            Nutrient values: Food Composition Table for Bangladesh, Institute of
            Nutrition and Food Science, University of Dhaka, 2013. Portion weights
            are our own assumption and are stated separately from the verified values.
          </p>
          <p className="text-[10.5px] text-[var(--text-faint)] shrink-0">
            Informational only — not medical advice.
          </p>
        </div>
      </footer>
    </div>
  );
}