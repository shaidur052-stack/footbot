// ThemeToggle.jsx — sun/moon switch. The icon crossfades and rotates,
// so the change reads as a transition rather than a swap.

import { motion, AnimatePresence } from "framer-motion";
import { useTheme } from "../context/ThemeContext";

export default function ThemeToggle({ className = "" }) {
  const { isDark, toggle } = useTheme();

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={`relative w-8 h-8 rounded-full flex items-center justify-center
                  text-[var(--text-dim)] hover:text-[var(--text)]
                  hover:bg-[var(--surface-2)] transition-colors ${className}`}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={isDark ? "moon" : "sun"}
          initial={{ opacity: 0, rotate: -60, scale: 0.7 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={{ opacity: 0, rotate: 60, scale: 0.7 }}
          transition={{ duration: 0.2 }}
          className="absolute text-[15px] leading-none"
        >
          {isDark ? "☾" : "☀"}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}