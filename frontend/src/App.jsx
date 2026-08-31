// App.jsx — providers, routes, page transitions.

import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import LandingPage from "./pages/LandingPage";
import AuthPage from "./pages/AuthPage";
import ProfileSetupPage from "./pages/ProfileSetupPage";
import ChatPage from "./pages/ChatPage";

function Page({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

function AnimatedRoutes() {
  const location = useLocation();
  const navigate = useNavigate();

  // key={location.pathname} tells AnimatePresence a NEW page arrived,
  // so it plays the old page's exit before mounting the new one.
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Page><LandingPage /></Page>} />
        <Route path="/signup" element={<Page><AuthPage mode="signup" /></Page>} />
        <Route path="/login" element={<Page><AuthPage mode="login" /></Page>} />
        <Route
          path="/setup"
          element={
            <Page>
              <ProfileSetupPage onDone={() => setTimeout(() => navigate("/chat"), 2000)} />
            </Page>
          }
        />
        <Route path="/chat" element={<Page><ChatPage /></Page>} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AnimatedRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}