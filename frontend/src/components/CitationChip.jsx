// CitationChip.jsx — where an answer's facts came from.
// This is the visible proof of grounding: no chip means no source.

import { motion } from "framer-motion";

export default function CitationChip({ sources }) {
  if (!sources || sources.length === 0) return null;   // refusal case

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {sources.map((s, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 320, damping: 22,
                        delay: 0.15 + i * 0.08 }}
          className="mono inline-flex items-center gap-1.5 px-2.5 py-1
                     rounded-full bg-[var(--surface)] border border-[var(--border-strong)]
                     text-[10.5px] text-[var(--brand)]"
        >
          <span className="font-medium">{s.food}</span>
          <span className="opacity-50">·</span>
          <span className="opacity-80">{s.portion}</span>
          <span className="opacity-50">·</span>
          <span className="opacity-60">{s.ref}</span>
        </motion.span>
      ))}
    </div>
  );
}