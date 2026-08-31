// LanguageToggle.jsx — BN / EN switch with a sliding pill.
// The pill is ONE element; layoutId animates it between positions.

import { motion } from "framer-motion";

const OPTIONS = [
  { code: "bn", label: "বাংলা" },
  { code: "en", label: "English" },
];

export default function LanguageToggle({ value, onChange }) {
  return (
    <div className="relative flex bg-gray-100 rounded-full p-0.5">
      {OPTIONS.map((opt) => {
        const isActive = value === opt.code;

        return (
          <button
            key={opt.code}
            onClick={() => onChange(opt.code)}
            className="relative px-3 py-1 text-xs font-medium rounded-full
                       transition-colors duration-200"
          >
            {isActive && (
              <motion.span
                layoutId="lang-pill"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
                className="absolute inset-0 bg-teal-600 rounded-full"
              />
            )}
            <span className={`relative z-10 ${isActive ? "text-white" : "text-gray-600"}`}>
              {opt.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}