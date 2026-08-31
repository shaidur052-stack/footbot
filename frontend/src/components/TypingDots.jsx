// TypingDots.jsx — the "bot is thinking" indicator.

import { motion } from "framer-motion";

export default function TypingDots() {
  const dotVariants = {
    animate: {
      y: [0, -6, 0],
      transition: { duration: 0.6, repeat: Infinity, ease: "easeInOut" },
    },
  };

  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          variants={dotVariants}
          animate="animate"
          transition={{ delay: i * 0.15 }}   // the stagger makes it a wave
          className="w-2 h-2 rounded-full bg-teal-500"
        />
      ))}
    </div>
  );
}