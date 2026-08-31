// MessageBubble.jsx — one chat message.
// Bot messages carry a streaming caret, citations, and feedback buttons.

import { motion } from "framer-motion";
import CitationChip from "./CitationChip";
import FeedbackButtons from "./FeedbackButtons";

/** Minimal inline formatting: **bold** and line breaks.
 *  A full markdown library is overkill for the shapes the model returns. */
function formatted(text) {
  return text.split("\n").map((line, i) => (
    <span key={i}>
      {i > 0 && <br />}
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={j}>{part.slice(2, -2)}</strong>
        ) : (
          part
        )
      )}
    </span>
  ));
}

export default function MessageBubble({ text, isUser, sources, isStreaming, messageId }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div className="max-w-[78%] flex flex-col items-start">
        <div
          className={`px-4 py-2.5 rounded-2xl text-[15px] leading-[1.6] ${
            isUser
              ? "bg-[var(--brand)] text-[var(--brand-text)] rounded-br-sm"
              : "bg-[var(--surface-2)] text-[var(--text)] rounded-bl-sm"
          }`}
        >
          {formatted(text)}
          {isStreaming && (
            <motion.span
              animate={{ opacity: [1, 0, 1] }}
              transition={{ duration: 0.8, repeat: Infinity }}
              className="inline-block w-[2px] h-[1em] ml-0.5 align-middle
                         bg-[var(--text-dim)]"
            />
          )}
        </div>

        {/* citations and feedback only once the answer is complete */}
        {!isUser && !isStreaming && (
          <>
            <CitationChip sources={sources} />
            <FeedbackButtons messageId={messageId} />
          </>
        )}
      </div>
    </motion.div>
  );
}