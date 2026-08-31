// AuthContext.jsx — who's signed in, available anywhere in the tree.

import { createContext, useContext, useState } from "react";
import * as api from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [email, setEmail] = useState(null);
  const [hasProfile, setHasProfile] = useState(false);

  async function signup(e, password) {
    const data = await api.signup(e, password);
    setEmail(e);
    setHasProfile(data.has_profile);
    return data;
  }

  async function login(e, password) {
    const data = await api.login(e, password);
    setEmail(e);
    setHasProfile(data.has_profile);
    return data;
  }

  function logout() {
    api.logout();
    setEmail(null);
    setHasProfile(false);
  }

  return (
    <AuthContext.Provider
      value={{ email, hasProfile, setHasProfile, signup, login, logout,
               isSignedIn: !!email }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}