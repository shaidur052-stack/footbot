// Sidebar.jsx — conversation history.
// Fixed on desktop, slides over on mobile. Anonymous users see the
// empty state, since nothing is saved for them.

import { motion, AnimatePresence } from "framer-motion";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar({
  conversations = [],
  activeId,
  onSelect,
  onNew,
  onDelete,
  open,
  onClose,
  email,
  onLogout,
  onSignIn,
}) {
  const panel = (
    <div className="flex flex-col h-full bg-[var(--surface-2)]
                    border-r border-[var(--border)]">

      {/* brand + theme */}
      <div className="flex items-center justify-between px-4 h-[60px]
                      border-b border-[var(--border)]">
        <div className="flex items-baseline gap-1.5">
          <span className="display text-[17px] font-semibold text-[var(--text)]">
            NutriBot
          </span>
          <span className="mono text-[9px] tracking-[0.18em] text-[var(--brand)]">
            BD
          </span>
        </div>
        <ThemeToggle />
      </div>

      {/* new chat */}
      <div className="p-3">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5
                     rounded-lg bg-[var(--brand)] text-[var(--brand-text)]
                     text-[13px] font-medium transition-opacity hover:opacity-90"
        >
          <span className="text-base leading-none">+</span>
          New chat
        </button>
      </div>

      {/* conversations */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 ? (
          <p className="px-3 py-6 text-[12px] text-[var(--text-faint)] leading-relaxed">
            {email
              ? "Your conversations will appear here."
              : "Sign in to keep your conversation history."}
          </p>
        ) : (
          <AnimatePresence initial={false}>
            {conversations.map((c) => (
              <motion.div
                key={c.id}
                layout
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                transition={{ duration: 0.18 }}
                className="group relative"
              >
                <button
                  onClick={() => onSelect(c.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg mb-0.5
                              transition-colors ${
                    c.id === activeId
                      ? "bg-[var(--surface)] shadow-[var(--shadow)]"
                      : "hover:bg-[var(--surface)]/60"}`}
                >
                  <div className="text-[13px] text-[var(--text)] truncate pr-6">
                    {c.title}
                  </div>
                  <div className="text-[11px] text-[var(--text-faint)] mt-0.5">
                    {c.message_count} messages
                  </div>
                </button>

                {/* delete appears on hover, so the list stays calm at rest */}
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
                  aria-label="Delete conversation"
                  className="absolute right-2 top-2.5 w-6 h-6 rounded
                             text-[var(--text-faint)] opacity-0
                             group-hover:opacity-100 hover:text-[var(--danger)]
                             hover:bg-[var(--border)] transition-all
                             text-base leading-none"
                >
                  ×
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* account */}
      <div className="p-3 border-t border-[var(--border)]">
        {email ? (
          <>
            <div className="text-[11px] text-[var(--text-faint)] truncate mb-1.5">
              {email}
            </div>
            <button
              onClick={onLogout}
              className="text-[12px] text-[var(--text-dim)]
                         hover:text-[var(--danger)] transition-colors"
            >
              Sign out
            </button>
          </>
        ) : (
          <button
            onClick={onSignIn}
            className="text-[12px] text-[var(--brand)] font-medium hover:underline"
          >
            Sign in
          </button>
        )}
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden md:block w-[260px] shrink-0">{panel}</aside>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={onClose}
              className="md:hidden fixed inset-0 bg-black/40 z-40"
            />
            <motion.aside
              initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
              className="md:hidden fixed left-0 top-0 bottom-0 w-[260px] z-50"
            >
              {panel}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}