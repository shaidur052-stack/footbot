// FeedbackButtons.jsx — thumbs up/down under each bot answer.

import { useState } from "react";
import { motion } from "framer-motion";
import { sendFeedback } from "../api";

export default function FeedbackButtons({ messageId }) {
  const [choice, setChoice] = useState(null);   // null | true | false

  function handleClick(isPositive) {
    if (choice !== null) return;                // one vote per answer
    setChoice(isPositive);
    sendFeedback(messageId, isPositive).catch(() => {});
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.4 }}
      className="flex gap-1 mt-1.5"
    >
      {[true, false].map((positive) => {
        const active = choice === positive;
        const dimmed = choice !== null && !active;

        return (
          <motion.button
            key={String(positive)}
            onClick={() => handleClick(positive)}
            whileTap={{ scale: 0.85 }}
            animate={active ? { scale: [1, 1.25, 1] } : {}}
            transition={{ duration: 0.3 }}
            disabled={choice !== null}
            className={`w-6 h-6 rounded-full text-[11px] flex items-center
                        justify-center border transition-colors
                        ${active
                          ? "bg-teal-600 border-teal-600 text-white"
                          : "border-gray-300 text-gray-400 hover:border-gray-400"}
                        ${dimmed ? "opacity-30" : ""}`}
          >
            {positive ? "▲" : "▼"}
          </motion.button>
        );
      })}
    </motion.div>
  );
}