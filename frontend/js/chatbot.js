import { api, requireAuth, bindLogout, showError, clearError } from "./api.js";

const messages = document.querySelector("#chat-messages");
const form = document.querySelector("#chat-form");
const textarea = document.querySelector("#question");
const errorBox = document.querySelector("#chat-error");
const status = document.querySelector("#history-status");
const historyList = document.querySelector("#history-list");
const sendButton = document.querySelector("#send-button");
bindLogout();

try {
  const user = await requireAuth();
  if (user) await loadHistory();
} catch {
  status.textContent = "Your chat history could not be loaded. Try refreshing.";
}

function addMessage(kind, text, details = {}) {
  const row = document.createElement("article");
  row.className = `${kind}-message message-row`;
  const avatar = document.createElement("span");
  avatar.className = "message-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = kind === "assistant" ? "C" : "You";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.append(paragraph);
  if (details.source || details.route) {
    const tag = document.createElement("span");
    tag.className = "source-tag";
    tag.textContent = details.source ? humanize(details.source) : humanize(details.route);
    bubble.append(tag);
  }
  if (Array.isArray(details.sources) && details.sources.length) {
    const sourceList = document.createElement("ul");
    sourceList.className = "source-list";
    for (const item of details.sources) {
      const li = document.createElement("li");
      li.textContent = [item.source, item.page ? `page ${item.page}` : ""].filter(Boolean).join(" · ") || "College document";
      sourceList.append(li);
    }
    bubble.append(sourceList);
  }
  row.append(avatar, bubble);
  messages.append(row);
  messages.scrollTop = messages.scrollHeight;
  return row;
}

function humanize(value) {
  return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = textarea.value.trim();
  if (!question) return;
  clearError(errorBox);
  addMessage("user", question);
  textarea.value = "";
  textarea.disabled = true;
  sendButton.disabled = true;
  sendButton.querySelector("span:first-child").textContent = "Thinking…";
  const pending = addMessage("assistant", "Working on your question…");
  try {
    const result = await api.chat(question);
    pending.remove();
    addMessage("assistant", result.answer || "The assistant returned no answer.", result);
    await loadHistory();
  } catch (error) {
    pending.remove();
    showError(errorBox, error.message);
  } finally {
    textarea.disabled = false;
    sendButton.disabled = false;
    sendButton.querySelector("span:first-child").textContent = "Send";
    textarea.focus();
  }
});

document.querySelector("#refresh-history").addEventListener("click", loadHistory);

async function loadHistory() {
  status.textContent = "Loading your history…";
  historyList.replaceChildren();
  try {
    const result = await api.history(50);
    const rows = result.messages || [];
    status.textContent = rows.length ? `${rows.length} recent conversation${rows.length === 1 ? "" : "s"}` : "No saved conversations yet.";
    for (const item of rows) {
      const article = document.createElement("article");
      article.className = "history-card";
      const header = document.createElement("div");
      header.className = "history-meta";
      const date = document.createElement("time");
      date.textContent = item.created_at ? new Date(item.created_at).toLocaleString() : "Saved conversation";
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.textContent = humanize(item.source || item.route);
      header.append(date, tag);
      const question = document.createElement("h3");
      question.textContent = item.question;
      const answer = document.createElement("p");
      answer.textContent = item.answer;
      article.append(header, question, answer);
      historyList.append(article);
    }
  } catch (error) {
    status.textContent = error.status === 401 ? "Sign in to view your history." : error.message;
  }
}
