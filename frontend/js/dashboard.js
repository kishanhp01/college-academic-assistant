import { api, requireAuth, bindLogout, showError } from "./api.js";

const errorBox = document.querySelector("#page-error");
bindLogout();
try {
  const user = await requireAuth();
  if (user) document.querySelector("#welcome-name").textContent = user.username ? `, ${user.username}` : "";
} catch {
  showError(errorBox, "Your account details could not be loaded. Please refresh the page.");
}
