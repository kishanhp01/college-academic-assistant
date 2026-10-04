const configuredBase = document.querySelector('meta[name="api-base-url"]')?.content?.trim();
export const API_BASE_URL = (configuredBase || window.location.origin).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
    });
  } catch {
    throw new ApiError("Could not reach the assistant service. Check that the backend is running.");
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof payload.error === "string" ? payload.error : "The request could not be completed.";
    if (response.status === 401 && !path.startsWith("/api/auth/login") && !path.startsWith("/api/auth/register")) {
      window.location.replace("./login.html");
    }
    throw new ApiError(message, response.status);
  }
  return payload;
}

const post = (path, data) => request(path, { method: "POST", body: JSON.stringify(data) });

export const api = {
  register: (data) => post("/api/auth/register", data),
  login: (data) => post("/api/auth/login", data),
  logout: () => post("/api/auth/logout", {}),
  me: () => request("/api/auth/me"),
  chat: (question) => post("/api/chat", { question }),
  history: (limit = 50) => request(`/api/chat/history?limit=${encodeURIComponent(limit)}`),
  generatePlan: (data) => post("/api/study-plan", data),
  modifyPlan: (data) => post("/api/study-plan/modify", data),
};

export async function requireAuth() {
  try {
    const result = await api.me();
    return result.user;
  } catch (error) {
    if (error.status === 401) {
      window.location.replace("./login.html");
      return null;
    }
    throw error;
  }
}

export function bindLogout() {
  const button = document.querySelector("#logout-button");
  button?.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await api.logout();
      window.location.replace("./login.html");
    } catch (error) {
      button.disabled = false;
      window.alert(error.message);
    }
  });
}

export function showError(element, message) {
  element.textContent = message;
  element.hidden = false;
}

export function clearError(element) {
  element.textContent = "";
  element.hidden = true;
}
