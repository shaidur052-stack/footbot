// api.js — the ONLY file that knows where data comes from.
// Components never fetch directly; they call these functions.

const USE_MOCK = false;
const BASE_URL = "http://localhost:8000";

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// ---------- AUTH TOKEN ----------
// Held in memory only, so a browser refresh signs the user out. Real apps
// use httpOnly cookies; for this project it is a documented limitation.

let authToken = null;

export function setToken(t) {
  authToken = t;
}

export function getToken() {
  return authToken;
}

function authHeaders() {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

/** FastAPI sends `detail` as a STRING for our own HTTPExceptions (409, 401)
 *  but as an ARRAY of objects for Pydantic validation failures (422).
 *  Rendering the array directly is what produces "[object Object]". */
function readError(body, fallback) {
  const detail = body?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    const field = first.loc?.[first.loc.length - 1];
    if (field === "email") return "Please enter a valid email address";
    if (field === "password") return "Password must be at least 8 characters";
    return first.msg || fallback;
  }

  return fallback;
}

// ---------- MOCK DATA ----------

const MOCK_ANSWERS = [
  {
    answer:
      "Ek plate bhat e (~250g) prai 272 calorie thake. Apnar daily target 2030 " +
      "calorie, tai ek plate bhat apnar dinner e fit kore.",
    language: "bn",
    sources: [
      { food: "Rice, BR-28, boiled", portion: "1 plate (250g)", ref: "INFS FCT (01_0037)" },
    ],
  },
  {
    answer:
      "One piece of ilish (75g) has about 13.5g of protein and 167 kcal. " +
      "It is the fattiest fish in the table, at 16.8g fat per 100g.",
    language: "en",
    sources: [
      { food: "Hilsha, without bones, raw", portion: "1 piece (75g)", ref: "INFS FCT (09_0033)" },
    ],
  },
  {
    answer:
      "That food is not in my Bangladeshi food database, so I will not guess. " +
      "I can only answer from verified local food data.",
    language: "en",
    sources: [],                                 // empty = the honest-refusal case
  },
];

let mockCounter = 0;

const MOCK_PROFILE = {
  age: 23,
  gender: "male",
  weight_kg: 70,
  height_cm: 173,
  activity: "sedentary",
  goal: "maintain",
  condition: "none",
  bmi: 23.4,
  daily_calories: 2030,
  consumed_today: 0,
};

// ---------- AUTH ----------

export async function signup(email, password) {
  const res = await fetch(`${BASE_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(readError(body, "Could not create the account"));
  }

  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export async function login(email, password) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  // The backend deliberately returns the same message for unknown email and
  // wrong password, so we don't leak which emails are registered either.
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(readError(body, "Incorrect email or password"));
  }

  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export function logout() {
  setToken(null);
}

// ---------- CHAT ----------

export async function sendMessage(message, conversationId = null, language = "bn") {
  if (USE_MOCK) {
    await delay(1500);
    const sample = MOCK_ANSWERS[mockCounter % MOCK_ANSWERS.length];
    mockCounter++;
    return { ...sample, message_id: Date.now(), conversation_id: conversationId };
  }

  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, conversation_id: conversationId, language }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}

// Streaming send. onChunk(text) fires per piece; resolves with sources,
// message_id and conversation_id.
//
// `language` is the UI toggle, not a guess from the message text: a user who
// selects Bangla and types in English still wants Bangla back.
export async function sendMessageStream(
  message,
  onChunk,
  conversationId = null,
  language = "bn",
) {
  if (USE_MOCK) {
    await delay(900);
    const sample = MOCK_ANSWERS[mockCounter % MOCK_ANSWERS.length];
    mockCounter++;

    const words = sample.answer.split(" ");
    for (const w of words) {
      await delay(45);
      onChunk(w + " ");
    }

    return { ...sample, message_id: Date.now(), conversation_id: conversationId };
  }

  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, conversation_id: conversationId, language }),
  });
  if (!res.ok) throw new Error("Stream failed");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const DELIM = "\n---META---\n";

  let buffer = "";        // everything received so far
  let emitted = 0;        // how much has already gone to onChunk
  let metaSeen = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const idx = buffer.indexOf(DELIM);
    if (idx !== -1) metaSeen = true;

    // Emit only text BEFORE the delimiter. Hold back a tail the length of
    // the delimiter, in case it arrives split across two network chunks.
    const safeEnd = metaSeen ? idx : Math.max(0, buffer.length - DELIM.length);
    if (safeEnd > emitted) {
      onChunk(buffer.slice(emitted, safeEnd));
      emitted = safeEnd;
    }
  }

  const idx = buffer.indexOf(DELIM);
  if (idx === -1) {
    return { sources: [], message_id: Date.now(), conversation_id: conversationId };
  }
  return JSON.parse(buffer.slice(idx + DELIM.length));
}

// ---------- CONVERSATIONS ----------

export async function listConversations() {
  if (USE_MOCK) return [];

  const res = await fetch(`${BASE_URL}/conversations`, { headers: authHeaders() });
  if (res.status === 401) return [];        // anonymous users have no history
  if (!res.ok) throw new Error("Could not load conversations");
  return res.json();
}

export async function getConversation(id) {
  const res = await fetch(`${BASE_URL}/conversations/${id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Could not load that conversation");
  return res.json();
}

export async function deleteConversation(id) {
  const res = await fetch(`${BASE_URL}/conversations/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Could not delete");
}

// ---------- PROFILE ----------

export async function getProfile() {
  if (USE_MOCK) {
    await delay(600);
    return MOCK_PROFILE;
  }

  const res = await fetch(`${BASE_URL}/profile`, { headers: authHeaders() });
  if (res.status === 404) return null;          // signed in, no profile yet
  if (!res.ok) throw new Error("Profile request failed");
  return res.json();
}

// Saves profile inputs; the backend computes bmi and daily_calories.
// The mock mirrors that math so no component ever does health arithmetic.
export async function saveProfile(profile) {
  if (USE_MOCK) {
    await delay(800);

    const { age, gender, weight_kg, height_cm, activity, goal } = profile;

    const bmr =
      gender === "male"
        ? 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        : 10 * weight_kg + 6.25 * height_cm - 5 * age - 161;

    const factors = { sedentary: 1.2, moderate: 1.55, active: 1.725 };
    let calories = bmr * (factors[activity] ?? 1.2);

    if (goal === "lose") calories -= 400;
    if (goal === "gain") calories += 400;

    // Same clinical floor the backend applies, so the two never disagree.
    const floor = gender === "male" ? 1500 : 1200;
    const heightM = height_cm / 100;

    return {
      ...profile,
      bmi: Number((weight_kg / (heightM * heightM)).toFixed(1)),
      daily_calories: Math.max(Math.round(calories), floor),
      consumed_today: 0,
    };
  }

  const res = await fetch(`${BASE_URL}/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(profile),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(readError(body, "Profile save failed"));
  }
  return res.json();
}

// ---------- FEEDBACK ----------

export async function sendFeedback(messageId, isPositive) {
  if (USE_MOCK) {
    await delay(200);
    console.log("mock feedback:", messageId, isPositive);
    return { ok: true };
  }

  const res = await fetch(`${BASE_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message_id: messageId, is_positive: isPositive }),
  });
  return res.json();
}