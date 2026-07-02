// content.js — injected into every page
// Responsible for extracting the user's highlighted text + surrounding context
// SECURITY: we only ever read text content, never innerHTML or execute anything from the page

const CONTEXT_CHARS = 1000; // chars to grab before and after highlight
const MAX_HIGHLIGHT_WORDS = 500;

function getSelectionData() {
  const selection = window.getSelection();

  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
    return { error: "no_selection" };
  }

  // Get the highlighted text as plain text only — never innerHTML
  const highlighted = selection.toString();

  if (!highlighted.trim()) {
    return { error: "no_selection" };
  }

  // Word count check
  const wordCount = highlighted.trim().split(/\s+/).length;
  if (wordCount > MAX_HIGHLIGHT_WORDS) {
    return { error: "too_long", wordCount };
  }

  // Get full page text as plain string — innerText strips all HTML/JS
  // This is safe: we're reading text only, never executing anything
  const fullPageText = document.body.innerText;

  // Find where the highlighted text appears in the full page text
  const highlightIndex = fullPageText.indexOf(highlighted.trim());

  let contextBefore = "";
  let contextAfter = "";

  if (highlightIndex !== -1) {
    // Clamp to page boundaries — handles first/last phrase edge cases
    const beforeStart = Math.max(0, highlightIndex - CONTEXT_CHARS);
    const afterEnd = Math.min(
      fullPageText.length,
      highlightIndex + highlighted.length + CONTEXT_CHARS
    );

    // Treat these as plain strings only
    contextBefore = String(fullPageText.slice(beforeStart, highlightIndex));
    contextAfter = String(
      fullPageText.slice(highlightIndex + highlighted.length, afterEnd)
    );
  }

  return {
    highlighted: String(highlighted), // enforce string type
    contextBefore,
    contextAfter,
    wordCount,
  };
}

// Listen for messages from popup.js
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "GET_SELECTION") {
    const data = getSelectionData();
    sendResponse(data);
  }
  // Return true to allow async sendResponse if needed later
  return true;
});
