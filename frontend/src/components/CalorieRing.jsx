// CalorieRing.jsx — animated progress ring, calories consumed vs target.

import { useEffect } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";

export default function CalorieRing({ consumed, target }) {
  const RADIUS = 52;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

  const ratio = Math.min(consumed / target, 1);   // clamp so it can't overflow

  // Motion value: animates without re-rendering React on every frame
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => Math.round(v));

  useEffect(() => {
    const controls = animate(count, consumed, { duration: 1.2, ease: "easeOut" });
    return controls.stop;
  }, [consumed, count]);

  return (
    <div className="relative w-[130px] h-[130px]">
      {/* -rotate-90 moves the stroke start from 3 o'clock to 12 o'clock */}
      <svg width="130" height="130" className="-rotate-90">
        <circle cx="65" cy="65" r={RADIUS} fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <motion.circle
          cx="65"
          cy="65"
          r={RADIUS}
          fill="none"
          stroke="#0d9488"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          initial={{ strokeDashoffset: CIRCUMFERENCE }}
          animate={{ strokeDashoffset: CIRCUMFERENCE * (1 - ratio) }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span className="text-2xl font-semibold text-gray-900">{rounded}</motion.span>
        <span className="text-[11px] text-gray-500">of {target} kcal</span>
      </div>
    </div>
  );
}