// RVKS WEB - Farm Owner / Admin Authentication Controller
import { Api } from "./api.js";
import { showToast } from "./utils.js";

export const Auth = {
  user: null,

  getCurrentUser() {
    return this.user || Api.getUser();
  },

  isLoggedIn() {
    const user = Api.getUser();
    return Api.isLoggedIn() && user && (user.role === "owner_admin" || user.role === "admin");
  },

  async handleLogin(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const usernameInput = document.getElementById("loginUsername");
    const passwordInput = document.getElementById("loginPassword");
    const username = usernameInput ? usernameInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value : "";

    if (!username || !password) {
      showToast("Missing Credentials", "error", "Please enter Admin username and password.");
      return false;
    }

    const submitBtn = document.getElementById("btnLoginSubmit") || document.querySelector("#formLogin button[type='submit']");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = "Authenticating Admin...";
    }

    try {
      const res = await Api.post("/api/auth/login", { username, password });
      
      // Strict role check: only owner_admin / admin allowed
      if (res.user.role !== "owner_admin" && res.user.role !== "admin") {
        throw new Error("Access denied. Only Farm Owner / Admin can access this system.");
      }

      Api.setToken(res.token);
      Api.setUser(res.user);
      Auth.user = res.user;

      // Section 1: Clear Login Success Toast
      showToast("Login Successful", "success", "Welcome back, Farm Owner!");

      Auth.checkAuth();
    } catch (err) {
      console.error("[RVKS] Login error:", err);
      const errMsg = err.message || "";
      if (
        errMsg.toLowerCase().includes("invalid") ||
        errMsg.toLowerCase().includes("credential") ||
        errMsg.toLowerCase().includes("password") ||
        errMsg.toLowerCase().includes("user") ||
        errMsg.toLowerCase().includes("401")
      ) {
        // Section 4: Invalid Login
        showToast("Invalid username or password", "error", "Please check your admin credentials and try again.");
      } else if (errMsg.toLowerCase().includes("access denied")) {
        // Section 4: Access Denied
        showToast("Access Denied", "error", "Admin / Farm Owner access only.");
      } else {
        showToast("Login Failed", "error", errMsg || "Check server or credentials.");
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = "Sign In to Admin Dashboard";
      }
    }
    return false;
  },

  checkAuth(onLoggedInCallback) {
    const user = Api.getUser();
    const loginView = document.getElementById("loginView");
    const appView = document.getElementById("appView");

    // Validate that the user exists and has the Admin role
    if (user && Api.isLoggedIn() && (user.role === "owner_admin" || user.role === "admin")) {
      Auth.user = user;

      // Update Header info
      const userNameEl = document.getElementById("currentUserName");
      if (userNameEl) userNameEl.innerText = user.full_name || user.username || "Farm Owner";

      const userRoleEl = document.getElementById("currentUserRole");
      if (userRoleEl) userRoleEl.innerText = "Owner / Admin";

      // Hide login, show app
      if (loginView) loginView.style.display = "none";
      if (appView) appView.style.display = "flex";

      // All admin features are always enabled for the Farm Owner
      document.querySelectorAll(".admin-only").forEach(el => el.style.display = "");

      if (typeof onLoggedInCallback === "function") {
        onLoggedInCallback(user);
      } else if (window.onAuthSuccess) {
        window.onAuthSuccess(user);
      }
    } else {
      // Not logged in or non-admin role
      if (user && user.role !== "owner_admin" && user.role !== "admin") {
        Api.clearAuth();
        showToast("Access Denied", "error", "Admin / Farm Owner access only.");
      }
      Auth.user = null;
      if (loginView) loginView.style.display = "flex";
      if (appView) appView.style.display = "none";
    }
  },

  applyRoleVisibility(role) {
    // Single-role architecture: Farm Owner has complete access to every module
    document.querySelectorAll(".admin-only").forEach(el => el.style.display = "");
  },

  async logout() {
    try {
      await Api.post("/api/auth/logout", {}).catch(() => {});
    } catch (e) {
      // Ignore network errors on logout
    }
    // Section 2 & 9: Clear session and redirect to Login Page first
    Api.clearAuth();
    Auth.user = null;
    Auth.checkAuth();

    // Section 2 & 9: Display Logout Success Toast on Login Screen
    showToast("Logged Out Successfully", "success", "See you again!");
  }
};

// Global session expiry listener (Section 4)
window.addEventListener("auth:unauthorized", () => {
  Api.clearAuth();
  Auth.user = null;
  Auth.checkAuth();
  showToast("Session Expired", "warning", "Your session has expired. Please log in again.");
});

// Expose on window for inline HTML onclick/onsubmit handlers
window.handleLogin = Auth.handleLogin.bind(Auth);
window.logout = Auth.logout.bind(Auth);
window.checkAuth = Auth.checkAuth.bind(Auth);
