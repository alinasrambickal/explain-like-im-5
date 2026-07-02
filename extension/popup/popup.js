// popup.js — controls the extension popup UI
// Talks to content.js (to get selection) and the FastAPI backend (to get explanation)
// SECURITY: all text is set via textContent, never innerHTML

const BACKEND_URL = "http://localhost:8000"; // change to deployed URL when live

// --- State ---
let currentSelection = null; // { highlighted, contextBefore, contextAfter }
let lastExplanation = null;  // track for "simplify more"
let simplifyLevel = 0;       // 0 = normal, 1 = simpler, 2 = simplest

// --- DOM refs ---
const states = {
  idle: document.getElementById("state-idle"),
  ready: document.getElementById("state-ready"),
  loading: document.getElementById("state-loading"),
  result: document.getElementById("state-result"),
  error: document.getElementById("state-error"),
};

const selectedTextEl = document.getElementById("selected-text");
const wordCountEl = document.getElementById("word-count");
const modelSelect = document.getElementById("model-select");
const explainBtn = document.getElementById("explain-btn");
const explanationTextEl = document.getElementById("explanation-text");
const errorTextEl = document.getElementById("error-text");
const simplifyBtn = document.getElementById("simplify-btn");
const resetBtn = document.getElementById("reset-btn");
const retryBtn = document.getElementById("retry-btn");

const usageEls = {
  gemini: {
    count: document.getElementById("usage-count-gemini"),
    fill: document.getElementById("usage-fill-gemini"),
  },
  groq: {
    count: document.getElementById("usage-count-groq"),
    fill: document.getElementById("usage-fill-groq"),
  },
  openrouter: {
    count: document.getElementById("usage-count-openrouter"),
    fill: document.getElementById("usage-fill-openrouter"),
  },
};

// --- State management ---
function showState(name) {
  Object.entries(states).forEach(([key, el]) => {
    el.classList.toggle("hidden", key !== name);
  });
}

// --- Usage bars ---
async function fetchUsage() {
  try {
    const response = await fetch(`${BACKEND_URL}/usage`);
    if (!response.ok) return;
    const data = await response.json();

    for (const [model, stats] of Object.entries(data.models)) {
      const els = usageEls[model];
      if (!els) continue;

      els.count.textContent = `${stats.used}/${stats.limit}`;
      els.fill.style.width = `${stats.percent_used}%`;
      els.fill.classList.toggle("usage-danger", stats.percent_used >= 90);
    }
  } catch {
    // Backend unreachable — leave bars at their last known state, don't error out the whole popup
  }
}

// --- Init: ask content script for current selection ---
async function init() {
  fetchUsage(); // fire-and-forget, don't block selection loading

  let tab;
  try {
    [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  } catch {
    showError("Couldn't access the current tab.");
    return;
  }

  chrome.tabs.sendMessage(tab.id, { type: "GET_SELECTION" }, (response) => {
    if (chrome.runtime.lastError || !response) {
      showState("idle");
      return;
    }

    if (response.error === "no_selection") {
      showState("idle");
      return;
    }

    if (response.error === "too_long") {
      showError(
        `That's ${response.wordCount} words — try highlighting under 500 words so the explanation stays focused.`
      );
      return;
    }

    currentSelection = response;
    simplifyLevel = 0;

    // Display preview — textContent only, never innerHTML
    selectedTextEl.textContent = response.highlighted;
    wordCountEl.textContent = `${response.wordCount} words`;
    showState("ready");
  });
}

// --- Explain ---
async function explain(simplify = false) {
  if (!currentSelection) return;

  const model = modelSelect.value;
  showState("loading");

  // Build prompt instruction based on simplify level
  let simplifyNote = "";
  if (simplify && simplifyLevel === 1) {
    simplifyNote = " Use even simpler words — imagine explaining to a 5-year-old who has never heard of this topic.";
    simplifyLevel = 2;
  } else if (simplify && simplifyLevel === 0) {
    simplifyNote = " Simplify your explanation a bit more.";
    simplifyLevel = 1;
  }

  let body;
  try {
    const response = await fetch(`${BACKEND_URL}/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        highlighted: currentSelection.highlighted,
        context_before: currentSelection.contextBefore,
        context_after: currentSelection.contextAfter,
        model,
        simplify_note: simplifyNote,
      }),
    });

    body = await response.json();

    if (!response.ok) {
      showError(body.detail || "Something went wrong. Try again.");
      return;
    }
  } catch {
    showError("Can't reach the backend. Make sure it's running.");
    return;
  }

  lastExplanation = body.explanation;

  // Set explanation text safely — textContent only, never innerHTML
  explanationTextEl.textContent = body.explanation;

  // Hide "simplify more" if we've already hit max simplification
  simplifyBtn.style.display = simplifyLevel >= 2 ? "none" : "inline-block";

  fetchUsage();
  showState("result");
}

function showError(msg) {
  // textContent only — safe rendering
  errorTextEl.textContent = msg;
  showState("error");
}

function reset() {
  currentSelection = null;
  lastExplanation = null;
  simplifyLevel = 0;
  simplifyBtn.style.display = "inline-block";
  init();
}

// --- Event listeners ---
explainBtn.addEventListener("click", () => explain(false));
simplifyBtn.addEventListener("click", () => explain(true));
resetBtn.addEventListener("click", reset);
retryBtn.addEventListener("click", reset);

// --- Boot ---
init();
