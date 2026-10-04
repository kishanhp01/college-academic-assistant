import { api, showError, clearError } from "./api.js";

const form = document.querySelector("#register-form");
const errorBox = document.querySelector("#form-error");
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError(errorBox);
  const data = new FormData(form);
  const username = data.get("username").trim();
  const email = data.get("email").trim();
  const password = data.get("password");
  if (!username || !email || !password.trim()) {
    showError(errorBox, "Please fill in all fields.");
    return;
  }
  if (password.length < 8) {
    showError(errorBox, "Use a password with at least 8 characters.");
    return;
  }
  if (password !== data.get("confirm-password")) {
    showError(errorBox, "The passwords do not match.");
    return;
  }
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Creating account…";
  try {
    await api.register({ username, email, password });
    window.location.replace("./login.html?registered=1");
  } catch (error) {
    showError(errorBox, error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Create account";
  }
});
