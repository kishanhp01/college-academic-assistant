import { api, showError, clearError } from "./api.js";

const form = document.querySelector("#login-form");
const errorBox = document.querySelector("#form-error");
if (new URLSearchParams(window.location.search).get("registered") === "1") {
  const notice = document.createElement("p");
  notice.className = "form-message success";
  notice.setAttribute("role", "status");
  notice.textContent = "Account created. Sign in to continue.";
  form.before(notice);
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError(errorBox);
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Signing in…";
  try {
    const data = new FormData(form);
    await api.login({ email: data.get("email").trim(), password: data.get("password") });
    window.location.replace("./dashboard.html");
  } catch (error) {
    showError(errorBox, error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Sign in";
  }
});
