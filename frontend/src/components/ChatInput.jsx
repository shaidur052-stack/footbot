// ChatInput.jsx — text box + send button.

import { useState } from "react";
import { motion } from "framer-motion";

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState("");

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="max-w-2xl mx-auto flex items-center gap-2
                      bg-[var(--surface)] border border-[var(--border-strong)]
                      rounded-full pl-4 pr-1.5 py-1.5
                      focus-within:border-[var(--brand)] transition-colors">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about any Bangladeshi food…"
          disabled={disabled}
          className="flex-1 bg-transparent text-[15px] text-[var(--text)]
                     placeholder:text-[var(--text-faint)] outline-none
                     disabled:text-[var(--text-faint)]"
        />

        <motion.button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          whileTap={{ scale: 0.9 }}
          aria-label="Send"
          className="w-9 h-9 shrink-0 rounded-full bg-[var(--brand)]
                     text-[var(--brand-text)] flex items-center justify-center
                     text-base transition-opacity
                     disabled:opacity-30 disabled:cursor-not-allowed"
        >
          ↑
        </motion.button>
      </div>

      <p className="text-center text-[11px] text-[var(--text-faint)] mt-2.5">
        Informational only — not medical advice.
      </p>
    </div>
  );
}