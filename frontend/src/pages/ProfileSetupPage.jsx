// ProfileSetupPage.jsx — collects the inputs that make advice specific.
// Uses theme tokens throughout, so it works in light and dark.

import { useState } from "react";
import { motion } from "framer-motion";
import { saveProfile } from "../api";
import CalorieRing from "../components/CalorieRing";
import ThemeToggle from "../components/ThemeToggle";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

export default function ProfileSetupPage({ onDone }) {
  const [form, setForm] = useState({
    age: 23,
    gender: "male",
    weight_kg: 70,
    height_cm: 173,
    activity: "sedentary",
    goal: "maintain",
    condition: "none",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  function update(key, value) {
    const numeric = ["age", "weight_kg", "height_cm"];
    setForm((prev) => ({
      ...prev,
      [key]: numeric.includes(key) ? Number(value) : value,
    }));
  }

  async function handleSubmit() {
    setSaving(true);
    setError(null);
    try {
      const saved = await saveProfile(form);
      setResult(saved);
      onDone?.(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Explicit background AND text colour on every control. Without both,
  // the browser default (black on white) fights the dark theme, and an
  // inherited light colour disappears on the light theme.
  const fieldCls =
    "w-full px-3 py-2.5 rounded-lg " +
    "bg-[var(--surface)] text-[var(--text)] " +
    "border border-[var(--border-strong)] text-[15px] " +
    "outline-none focus:border-[var(--brand)] transition-colors";

  // ---- after saving ----
  if (result) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6 bg-[var(--bg)]">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 22 }}
          className="w-full max-w-md p-8 rounded-2xl bg-[var(--surface)]
                     border border-[var(--border)] text-center"
        >
          <h2 className="display text-xl font-semibold text-[var(--text)] mb-1">
            Your daily target
          </h2>
          <p className="text-[12px] text-[var(--text-dim)] mb-6">
            BMI {result.bmi} · goal: {result.goal}
          </p>

          <div className="flex justify-center">
            <CalorieRing
              consumed={result.consumed_today}
              target={result.daily_calories}
            />
          </div>

          <p className="text-[12px] text-[var(--text-dim)] mt-6">
            Every answer will now be measured against these numbers.
          </p>
        </motion.div>
      </div>
    );
  }

  // ---- the form ----
  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12 bg-[var(--bg)]">
      <div className="absolute top-5 right-5"><ThemeToggle /></div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="w-full max-w-md p-7 rounded-2xl bg-[var(--surface)]
                   border border-[var(--border)]"
      >
        <motion.h2 variants={item}
                   className="display text-xl font-semibold text-[var(--text)] mb-1">
          Tell us about you
        </motion.h2>
        <motion.p variants={item}
                  className="text-[13px] text-[var(--text-dim)] mb-6">
          This is what makes the advice yours, not generic.
        </motion.p>

        <motion.div variants={item} className="grid grid-cols-2 gap-3 mb-3">
          <Field label="Age">
            <input type="number" min="10" max="100" value={form.age}
                   onChange={(e) => update("age", e.target.value)}
                   className={fieldCls} />
          </Field>
          <Field label="Gender">
            <select value={form.gender}
                    onChange={(e) => update("gender", e.target.value)}
                    className={fieldCls}>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </Field>
        </motion.div>

        <motion.div variants={item} className="grid grid-cols-2 gap-3 mb-3">
          <Field label="Weight (kg)">
            <input type="number" min="25" max="200" value={form.weight_kg}
                   onChange={(e) => update("weight_kg", e.target.value)}
                   className={fieldCls} />
          </Field>
          <Field label="Height (cm)">
            <input type="number" min="100" max="230" value={form.height_cm}
                   onChange={(e) => update("height_cm", e.target.value)}
                   className={fieldCls} />
          </Field>
        </motion.div>

        <motion.div variants={item} className="mb-3">
          <Field label="Activity level">
            <select value={form.activity}
                    onChange={(e) => update("activity", e.target.value)}
                    className={fieldCls}>
              <option value="sedentary">Mostly sitting</option>
              <option value="moderate">Moderately active</option>
              <option value="active">Very active</option>
            </select>
          </Field>
        </motion.div>

        <motion.div variants={item} className="grid grid-cols-2 gap-3 mb-6">
          <Field label="Goal">
            <select value={form.goal}
                    onChange={(e) => update("goal", e.target.value)}
                    className={fieldCls}>
              <option value="lose">Lose weight</option>
              <option value="maintain">Maintain</option>
              <option value="gain">Gain weight</option>
            </select>
          </Field>
          <Field label="Condition">
            <select value={form.condition}
                    onChange={(e) => update("condition", e.target.value)}
                    className={fieldCls}>
              <option value="none">None</option>
              <option value="diabetes">Diabetes</option>
              <option value="hypertension">High blood pressure</option>
            </select>
          </Field>
        </motion.div>

        {error && (
          <p className="mb-4 text-[13px] text-[var(--danger)]">{error}</p>
        )}

        <motion.button
          variants={item}
          onClick={handleSubmit}
          disabled={saving}
          whileTap={{ scale: 0.98 }}
          className="w-full py-3 rounded-full bg-[var(--brand)]
                     text-[var(--brand-text)] text-[15px] font-medium
                     transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {saving ? "Calculating…" : "Continue"}
        </motion.button>

        <p className="mt-5 text-center text-[11px] text-[var(--text-faint)] leading-relaxed">
          Targets use the Mifflin-St Jeor equation and are informational only.
          Talk to a doctor before making significant dietary changes.
        </p>
      </motion.div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] text-[var(--text-dim)] mb-1.5">
        {label}
      </span>
      {children}
    </label>
  );
}