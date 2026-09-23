// RVKS WEB - API Client & Offline Fallback Interceptor

const API_BASE = window.location.origin;

export const Api = {
  getToken() {
    return localStorage.getItem("rvks_token") || "";
  },

  setToken(token) {
    localStorage.setItem("rvks_token", token);
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem("rvks_user") || "null");
    } catch {
      return null;
    }
  },

  setUser(user) {
    localStorage.setItem("rvks_user", JSON.stringify(user));
  },

  clearAuth() {
    localStorage.removeItem("rvks_token");
    localStorage.removeItem("rvks_user");
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        // Token expired or invalid
        this.clearAuth();
        window.dispatchEvent(new CustomEvent("auth:unauthorized"));
        throw new Error("Session expired. Please log in again.");
      }

      // Check if CSV or non-json response
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("text/csv")) {
        return await response.blob();
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.message || "Request failed");
      }
      return data;
    } catch (error) {
      // Check if purely network failure (offline)
      if (!navigator.onLine || error.message.includes("Failed to fetch")) {
        error.isOffline = true;
      }
      throw error;
    }
  },

  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const fullUrl = query ? `${endpoint}?${query}` : endpoint;
    return this.request(fullUrl, { method: "GET" });
  },

  post(endpoint, body = {}) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  put(endpoint, body = {}) {
    return this.request(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  patch(endpoint, body = {}) {
    return this.request(endpoint, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }
};
