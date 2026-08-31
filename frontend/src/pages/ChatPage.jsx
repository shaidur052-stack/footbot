// ChatPage.jsx — the chat shell: sidebar, header, messages, input.

import { useState, useRef, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

import * as api from "../api";
import { useAuth } from "../context/AuthContext";
import Sidebar from "../components/Sidebar";
import MessageBubble from "../components/MessageBubble";
import TypingDots from "../components/TypingDots";
import ChatInput from "../components/ChatInput";
import LanguageToggle from "../components/LanguageToggle";

const SUGGESTIONS = [
  { bn: "ভাতে কত ক্যালরি?", roman: "bhat e koto calorie?" },
  { bn: "ইলিশে কত প্রোটিন?", roman: "ilish e koto protein?" },
  { bn: "রুই নাকি ইলিশ?", roman: "rui naki ilish, kon ta beshi calorie?" },
  { bn: "দিনে কতটুকু ভাত খাব?", roman: "ami kototuku vat khabo akdin a?" },
];

export default function ChatPage() {
  const navigate = useNavigate();
  const auth = useAuth();

  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [isWaiting, setIsWaiting] = useState(false);
  const [language, setLanguage] = useState("bn");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef(null);

  const refreshList = useCallback(async () => {
    if (!auth.isSignedIn) return;
    try {
      setConversations(await api.listConversations());
    } catch {
      /* history is a nicety — never block the chat on it */
    }
  }, [auth.isSignedIn]);

  useEffect(() => { refreshList(); }, [refreshList]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isWaiting]);

  async function openConversation(id) {
    setSidebarOpen(false);
    try {
      const conv = await api.getConversation(id);
      setActiveId(id);
      setMessages(
        conv.messages.map((m) => ({
          id: m.id,
          text: m.content,
          isUser: m.role === "user",
          sources: m.sources,
        }))
      );
    } catch {
      /* deleted elsewhere, or not ours */
    }
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setSidebarOpen(false);
  }

  async function removeConversation(id) {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (id === activeId) newChat();
    try { await api.deleteConversation(id); } catch { refreshList(); }
  }

  async function handleSend(text) {
    const userMsg = { id: `u${Date.now()}`, text, isUser: true };
    setMessages((prev) => [...prev, userMsg]);
    setIsWaiting(true);

    const botId = `b${Date.now()}`;
    let firstChunk = true;

    try {
      const res = await api.sendMessageStream(
        text,
        (chunk) => {
          if (firstChunk) {
            // First token arrived -> hide dots, create the empty bubble
            firstChunk = false;
            setIsWaiting(false);
            setMessages((prev) => [
              ...prev,
              { id: botId, text: "", isUser: false, sources: [], isStreaming: true },
            ]);
          }
          setMessages((prev) =>
            prev.map((m) => (m.id === botId ? { ...m, text: m.text + chunk } : m))
          );
        },
        activeId,
        language,          // the header toggle decides the reply language
      );

      setMessages((prev) =>
        prev.map((m) =>
          m.id === botId
            ? { ...m, id: res.message_id ?? botId,
                sources: res.sources, isStreaming: false }
            : m
        )
      );

      // Only refresh the sidebar when a NEW conversation was created.
      // Refetching on every message re-mounts the list and makes it look
      // like duplicates are appearing.
      if (res.conversation_id && res.conversation_id !== activeId) {
        setActiveId(res.conversation_id);
        refreshList();
      } else if (activeId) {
        setConversations((prev) =>
          prev.map((c) =>
            c.id === activeId ? { ...c, message_count: c.message_count + 2 } : c
          )
        );
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `e${Date.now()}`, text: "Something went wrong. Try again.", isUser: false },
      ]);
    } finally {
      setIsWaiting(false);
    }
  }

  return (
    <div className="flex h-screen bg-[var(--bg)]">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={openConversation}
        onNew={newChat}
        onDelete={removeConversation}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        email={auth.email}
        onLogout={() => { auth.logout(); navigate("/"); }}
        onSignIn={() => navigate("/login")}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between px-4 h-[60px]
                           border-b border-[var(--border)] shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open history"
            className="md:hidden w-8 h-8 rounded-lg text-[var(--text-dim)]
                       hover:bg-[var(--surface-2)] transition-colors"
          >
            ☰
          </button>

          <div className="hidden md:block text-[13px] text-[var(--text-dim)] truncate">
            {activeId
              ? conversations.find((c) => c.id === activeId)?.title
              : "New chat"}
          </div>

          {/* Decides the reply language regardless of what the user types in */}
          <LanguageToggle value={language} onChange={setLanguage} />
        </header>

        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="h-full flex flex-col items-center justify-center px-6"
            >
              <h1 className="display text-[1.7rem] font-semibold text-[var(--text)] mb-2">
                What are you eating today?
              </h1>
              <p className="text-[14px] text-[var(--text-dim)] mb-8 text-center max-w-sm">
                Ask in Bangla, English, or however you type. Every answer cites
                the national food composition table.
              </p>

              <div className="grid sm:grid-cols-2 gap-2 w-full max-w-lg">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button
                    key={s.roman}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 + i * 0.06 }}
                    onClick={() => handleSend(s.roman)}
                    className="text-left px-4 py-3 rounded-xl bg-[var(--surface)]
                               border border-[var(--border)] hover:border-[var(--brand)]
                               transition-colors"
                  >
                    <div className="bn text-[14px] text-[var(--text)]">{s.bn}</div>
                    <div className="mono text-[10.5px] text-[var(--text-faint)] mt-0.5">
                      {s.roman}
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          ) : (
            <div className="max-w-2xl mx-auto px-4 py-6">
              <AnimatePresence>
                {messages.map((m) => (
                  <MessageBubble
                    key={m.id}
                    messageId={m.id}
                    text={m.text}
                    isUser={m.isUser}
                    sources={m.sources}
                    isStreaming={m.isStreaming}
                  />
                ))}
              </AnimatePresence>
              {isWaiting && <TypingDots />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <ChatInput onSend={handleSend} disabled={isWaiting} />
      </div>
    </div>
  );
}