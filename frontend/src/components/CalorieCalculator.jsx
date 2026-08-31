// CalorieCalculator.jsx — the landing page's interactive proof.
// Uses the SAME Mifflin-St Jeor formula as backend/app/services/profile_service.py,
// so the number here matches what the user sees after signing up.
// The food translation uses real per-100g values from the FCT.

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";

const ACTIVITY = {
  sedentary: { f: 1.2, label: "Mostly sitting" },
  moderate: { f: 1.55, label: "Moderately active" },
  active: { f: 1.725, label: "Very active" },
};

const GOALS = {
  lose: { adj: -400, label: "Lose weight" },
  maintain: { adj: 0, label: "Stay the same" },
  gain: { adj: 400, label: "Gain weight" },
};

// WHO recommends lower BMI cut-offs for South Asian populations, where
// cardiometabolic risk appears at a lower body mass than in European ones.
const BMI_BANDS = [
  { max: 18.5, label: "Below healthy range", tone: "#C68A2E" },
  { max: 23.0, label: "Healthy range", tone: "#0F766E" },
  { max: 27.5, label: "Above healthy range", tone: "#C68A2E" },
  { max: 99, label: "Well above healthy range", tone: "#B0453A" },
];

// Real rows from the database — kcal per typical portion.
const FOODS = [
  { bn: "ভাত", en: "plates of bhat", kcal: 272, code: "01_0037" },
  { bn: "ডাল", en: "bowls of mosur dal", kcal: 233, code: "02_0015" },
  { bn: "রুটি", en: "ruti", kcal: 98, code: "01_0042" },
  { bn: "শাক", en: "bowls of palong shak", kcal: 47, code: "04_0035" },
];

export default function CalorieCalculator() {
  const [f, setF] = useState({
    gender: "male",
    age: 23,
    height: 168,
    weight: 65,
    activity: "sedentary",
    goal: "maintain",
  });

  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));

  const result = useMemo(() => {
    const { gender, age, height, weight, activity, goal } = f;
    if (!age || !height || !weight) return null;

    // Mifflin-St Jeor
    const base = 10 * weight + 6.25 * height - 5 * age;
    const bmr = gender === "male" ? base + 5 : base - 161;
    const tdee = bmr * ACTIVITY[activity].f;

    // Floor the target. A flat deficit can drive small users to an
    // unsafely low intake, so clamp to widely used clinical minimums.
    const floor = gender === "male" ? 1500 : 1200;
    const raw = tdee + GOALS[goal].adj;
    const calories = Math.max(Math.round(raw), floor);
    const floored = raw < floor;

    const m = height / 100;
    const bmi = weight / (m * m);
    const band = BMI_BANDS.find((b) => bmi < b.max) ?? BMI_BANDS.at(-1);

    // position on a 15–35 scale, for the marker
    const pct = Math.min(Math.max(((bmi - 15) / 20) * 100, 2), 98);

    return { calories, bmi: bmi.toFixed(1), band, pct, floored };
  }, [f]);

  const inputCls =
    "w-full px-3 py-2.5 rounded-lg border border-[#0B2E2A]/15 bg-white text-[15px] " +
    "outline-none focus:border-[#0F766E] focus:ring-2 focus:ring-[#0F766E]/15";

  return (
    <div className="rounded-3xl border border-[#0B2E2A]/10 bg-white overflow-hidden">
      <div className="grid md:grid-cols-2">

        {/* ---------- inputs ---------- */}
        <div className="p-7 md:p-8 border-b md:border-b-0 md:border-r border-[#0B2E2A]/8">
          <div style={{ fontFamily: "var(--font-mono)" }}
               className="text-[10px] tracking-[0.2em] uppercase text-[#0F766E] mb-5">
            Your numbers
          </div>

          {/* gender — segmented, not a dropdown; two options don't need one */}
          <div className="flex gap-2 mb-4">
            {["male", "female"].map((g) => (
              <button key={g} onClick={() => set("gender", g)}
                className={`flex-1 py-2.5 rounded-lg text-sm font-medium capitalize
                            border transition-colors ${
                  f.gender === g
                    ? "bg-[#0B2E2A] text-white border-[#0B2E2A]"
                    : "bg-white text-[#3C4F4B] border-[#0B2E2A]/15 hover:border-[#0F766E]"}`}>
                {g}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <Field label="Age">
              <input type="number" min="10" max="100" value={f.age}
                     onChange={(e) => set("age", Number(e.target.value))} className={inputCls} />
            </Field>
            <Field label="Height (cm)">
              <input type="number" min="100" max="230" value={f.height}
                     onChange={(e) => set("height", Number(e.target.value))} className={inputCls} />
            </Field>
            <Field label="Weight (kg)">
              <input type="number" min="25" max="200" value={f.weight}
                     onChange={(e) => set("weight", Number(e.target.value))} className={inputCls} />
            </Field>
          </div>

          <Field label="Daily activity">
            <select value={f.activity} onChange={(e) => set("activity", e.target.value)}
                    className={inputCls}>
              {Object.entries(ACTIVITY).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </Field>

          <div className="h-4" />

          <Field label="Goal">
            <select value={f.goal} onChange={(e) => set("goal", e.target.value)}
                    className={inputCls}>
              {Object.entries(GOALS).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </Field>
        </div>

        {/* ---------- results ---------- */}
        <div className="p-7 md:p-8 bg-[#ECF5F2]">
          {result && (
            <>
              <div style={{ fontFamily: "var(--font-mono)" }}
                   className="text-[10px] tracking-[0.2em] uppercase text-[#0F766E] mb-5">
                Daily energy
              </div>

              <div className="flex items-baseline gap-2">
                <AnimatePresence mode="popLayout">
                  <motion.span key={result.calories}
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}
                    style={{ fontFamily: "var(--font-display)" }}
                    className="text-5xl font-semibold text-[#0B2E2A] leading-none">
                    {result.calories.toLocaleString()}
                  </motion.span>
                </AnimatePresence>
                <span className="text-sm text-[#5C6B68]">kcal / day</span>
              </div>

              {result.floored && (
                <p className="mt-2 text-[12px] text-[#B0453A] leading-relaxed">
                  Held at a safe minimum. A steeper cut isn't advisable at your size —
                  talk to a doctor or dietitian before going lower.
                </p>
              )}

              {/* BMI scale */}
              <div className="mt-8">
                <div className="flex items-baseline justify-between mb-2">
                  <span className="text-[13px] text-[#5C6B68]">BMI</span>
                  <span className="text-[15px] font-semibold" style={{ color: result.band.tone }}>
                    {result.bmi} · {result.band.label}
                  </span>
                </div>

                <div className="relative h-2 rounded-full bg-white overflow-hidden">
                  <div className="absolute inset-0 flex">
                    <div className="w-[17.5%] bg-[#E8C87E]" />
                    <div className="w-[22.5%] bg-[#0F766E]" />
                    <div className="w-[22.5%] bg-[#E8A32D]" />
                    <div className="flex-1 bg-[#D08A80]" />
                  </div>
                  <motion.div
                    animate={{ left: `${result.pct}%` }}
                    transition={{ type: "spring", stiffness: 220, damping: 26 }}
                    className="absolute -top-1 w-1 h-4 rounded-full bg-[#0B2E2A] shadow"
                    style={{ marginLeft: -2 }} />
                </div>

                <div style={{ fontFamily: "var(--font-mono)" }}
                     className="flex justify-between mt-1.5 text-[10px] text-[#5C6B68]">
                  <span>15</span><span>18.5</span><span>23</span><span>27.5</span><span>35</span>
                </div>

                <p className="mt-3 text-[11px] text-[#5C6B68] leading-relaxed">
                  Using the WHO cut-offs for South Asian populations, where health
                  risk appears at a lower BMI than the standard bands.
                </p>
              </div>

              {/* the part a generic calculator can't do */}
              <div className="mt-8 pt-6 border-t border-[#0B2E2A]/10">
                <div className="text-[13px] font-medium mb-3">In food you actually eat</div>
                <div className="space-y-2">
                  {FOODS.map((food) => (
                    <div key={food.code} className="flex items-baseline gap-2 text-[13px]">
                      <span className="font-semibold text-[#0F766E] tabular-nums w-8">
                        {Math.round(result.calories / food.kcal)}
                      </span>
                      <span style={{ fontFamily: "var(--font-bn)" }} className="text-[#0B2E2A]">
                        {food.bn}
                      </span>
                      <span className="text-[#5C6B68]">— {food.en}</span>
                      <span style={{ fontFamily: "var(--font-mono)" }}
                            className="ml-auto text-[10px] text-[#5C6B68]">{food.code}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[11px] text-[#5C6B68]">
                  Each row is a whole day of only that food — a rough sense of scale,
                  not a meal plan.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] text-[#5C6B68] mb-1.5">{label}</span>
      {children}
    </label>
  );
}