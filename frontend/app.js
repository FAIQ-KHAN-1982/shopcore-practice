/* =====================================================
   app.js — ShopCore Frontend Logic
   Beginner-friendly, no frameworks, vanilla JS only.

   API ENDPOINTS USED:
   ┌──────────────────────────────────────────────────────────┐
   │  POST  /auth/register               → registerUser()     │
   │  POST  /auth/login                  → loginUser()        │
   │  GET   /auth/verify                 → handleVerifyToken()│
   │  POST  /auth/refresh                → simulateTokenRefresh()│
   │  POST  /auth/logout                 → logoutUser()       │
   │  POST  /auth/forgot-password        → forgotPassword()   │
   │  POST  /auth/reset-password         → resetPassword()    │
   │  POST  /auth/change-password        → changePassword()   │
   │  POST  /auth/oauth/google/callback  → acceptGoogleConsent()│
   │  GET   /admin/users                 → renderAdminPanel() │
   │  POST  /admin/users/{id}/lock       → lockUser()         │
   │  POST  /admin/users/{id}/unlock     → unlockUser()       │
   │  GET   /seller/dashboard            → testSellerRoute()  │
   │  GET   /seller/products/{id}/modify → testSellerModify() │
   └──────────────────────────────────────────────────────────┘
===================================================== */

const API_BASE = "http://localhost:8000";

// ─────────────────────────────────────────────────
//  PANEL / TAB NAVIGATION
// ─────────────────────────────────────────────────
function showTab(name) {
  // Hide every panel
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
  // Remove "active" from all tab buttons
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));

  // Show the target panel
  const panel = document.getElementById("panel-" + name);
  if (panel) panel.classList.add("active");

  // Highlight the matching nav tab button (register / login only)
  const btn = document.getElementById("tab-" + name);
  if (btn) btn.classList.add("active");

  // Hide nav tabs container if not on register/login
  const navTabs = document.getElementById("nav-tabs-container");
  if (name === "dashboard" || name === "verify" || name === "forgot" || name === "reset" || name === "google-consent") {
    navTabs.style.display = "none";
  } else {
    navTabs.style.display = "flex";
  }
}

// ─────────────────────────────────────────────────
//  SHOW TOAST
// ─────────────────────────────────────────────────
function showToast(id, message, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = "toast " + type;   // sets color class
  el.classList.remove("hidden");

  // Auto-hide after 5 seconds
  setTimeout(() => {
    el.classList.add("hidden");
    el.className = "toast hidden";
  }, 5000);
}

// ─────────────────────────────────────────────────
//  TOGGLE PASSWORD VISIBILITY (👁)
// ─────────────────────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "🙈";
  } else {
    input.type = "password";
    btn.textContent = "👁";
  }
}

// ─────────────────────────────────────────────────
//  PASSWORD STRENGTH METER
// ─────────────────────────────────────────────────
function calculateStrength(password) {
  let score = 0;
  if (password.length >= 8)          score++;
  if (/[A-Z]/.test(password))        score++;
  if (/[0-9]/.test(password))        score++;
  if (/[\W_]/.test(password))        score++;
  return score;
}

function updateStrengthBar(score, barId, labelId) {
  const bar   = document.getElementById(barId);
  const label = document.getElementById(labelId);
  if (!bar || !label) return;

  const levels = [
    { pct: "0%",   color: "transparent",   text: "" },
    { pct: "25%",  color: "#f87171",        text: "Weak" },
    { pct: "50%",  color: "#fbbf24",        text: "Fair" },
    { pct: "75%",  color: "#60a5fa",        text: "Good" },
    { pct: "100%", color: "#34d399",        text: "Strong ✓" },
  ];

  const level = levels[score];
  bar.style.width      = level.pct;
  bar.style.background = level.color;
  label.textContent    = level.text;
  label.style.color    = level.color;
}

function updateStrength(password) {
  const score = calculateStrength(password);
  updateStrengthBar(score, "strength-bar", "strength-label");
}

function updateResetStrength(password) {
  const score = calculateStrength(password);
  updateStrengthBar(score, "reset-strength-bar", "reset-strength-label");
}

// ─────────────────────────────────────────────────
//  SET LOADING STATE
// ─────────────────────────────────────────────────
function setLoading(btnId, spinnerId, loading) {
  const btn     = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  if (!btn || !spinner) return;

  btn.disabled = loading;
  if (loading) {
    spinner.classList.remove("hidden");
    const textSpan = btn.querySelector(".btn-text");
    if (textSpan) textSpan.style.opacity = "0.5";
  } else {
    spinner.classList.add("hidden");
    const textSpan = btn.querySelector(".btn-text");
    if (textSpan) textSpan.style.opacity = "1";
  }
}

// ═════════════════════════════════════════════════
//  API CALL — REGISTER
// ═════════════════════════════════════════════════
async function registerUser(event) {
  event.preventDefault();

  const email      = document.getElementById("reg-email").value.trim();
  const password   = document.getElementById("reg-password").value;
  const first_name = document.getElementById("reg-first-name").value.trim();
  const last_name  = document.getElementById("reg-last-name").value.trim();
  const phone      = document.getElementById("reg-phone").value.trim() || null;
  const role       = document.getElementById("reg-role").value;

  if (!email || !password || !first_name || !last_name) {
    showToast("register-toast", "Please fill in all required fields.", "error");
    return;
  }

  setLoading("register-btn", "reg-spinner", true);

  try {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, first_name, last_name, phone, role }),
    });

    const data = await response.json();

    if (response.ok) {
      showToast(
        "register-toast",
        `🎉 Account created for ${data.first_name}! Verify your account via the link in the mock console log.`,
        "success"
      );
      document.getElementById("register-form").reset();
      updateStrength("");
    } else {
      const errMsg = data.detail || "Registration failed. Please try again.";
      showToast("register-toast", errMsg, "error");
    }
  } catch (err) {
    showToast("register-toast", "Cannot reach the server. Is FastAPI running?", "error");
    console.error("Register error:", err);
  } finally {
    setLoading("register-btn", "reg-spinner", false);
  }
}

// ═════════════════════════════════════════════════
//  API CALL — LOGIN
// ═════════════════════════════════════════════════
async function loginUser(event) {
  event.preventDefault();

  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  if (!email || !password) {
    showToast("login-toast", "Please enter your email and password.", "error");
    return;
  }

  setLoading("login-btn", "login-spinner", true);

  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (response.ok) {
      sessionStorage.setItem("access_token", data.access_token);
      sessionStorage.setItem("refresh_token", data.refresh_token);
      sessionStorage.setItem("user", JSON.stringify(data.user));

      renderDashboard(data.user, data.access_token, data.refresh_token);
      showTab("dashboard");

      document.getElementById("login-form").reset();
    } else {
      const errMsg = data.detail || "Login failed. Check your credentials.";
      showToast("login-toast", errMsg, "error");
    }
  } catch (err) {
    showToast("login-toast", "Cannot reach the server. Is FastAPI running?", "error");
    console.error("Login error:", err);
  } finally {
    setLoading("login-btn", "login-spinner", false);
  }
}

// ═════════════════════════════════════════════════
//  API CALL — MOCK GOOGLE LOGIN
// ═════════════════════════════════════════════════
function initiateGoogleLogin() {
  showTab("google-consent");
}

async function acceptGoogleConsent() {
  const prefix = document.getElementById("google-mock-prefix").value.trim();
  if (!prefix) return;

  const mockCode = prefix; // Representing email prefix in simulator

  try {
    const response = await fetch(`${API_BASE}/auth/oauth/google/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: mockCode }),
    });

    const data = await response.json();

    if (response.ok) {
      sessionStorage.setItem("access_token", data.access_token);
      sessionStorage.setItem("refresh_token", data.refresh_token);
      sessionStorage.setItem("user", JSON.stringify(data.user));

      renderDashboard(data.user, data.access_token, data.refresh_token);
      showTab("dashboard");
    } else {
      alert("Google login failed: " + (data.detail || "Unknown error"));
      showTab("login");
    }
  } catch (err) {
    alert("Cannot reach backend server to complete Google OAuth.");
    showTab("login");
  }
}

// ─────────────────────────────────────────────────
//  RENDER DASHBOARD
// ─────────────────────────────────────────────────
function renderDashboard(user, accessToken, refreshToken) {
  // Initials for the avatar circle
  const initials = (user.first_name?.[0] || "") + (user.last_name?.[0] || "");
  document.getElementById("user-avatar").textContent = initials.toUpperCase();

  // Name, email, verification & role
  document.getElementById("dashboard-name").textContent = `Hello, ${user.first_name}! 👋`;
  document.getElementById("dashboard-email").textContent = user.email;

  const verifyBadge = document.getElementById("verify-badge");
  if (user.is_verified) {
    verifyBadge.textContent = "✅ Verified";
    verifyBadge.className = "badge verified";
  } else {
    verifyBadge.textContent = "⏳ Unverified";
    verifyBadge.className = "badge";
  }

  const roleBadge = document.getElementById("role-badge");
  roleBadge.textContent = user.role.toUpperCase();
  if (user.role === "admin" || user.role === "superadmin") {
    roleBadge.style.background = "#8b5cf6"; // Purple for admins
  } else if (user.role === "seller") {
    roleBadge.style.background = "#3b82f6"; // Blue for sellers
  } else {
    roleBadge.style.background = "#10b981"; // Green for buyers
  }

  // Info grid (id, phone, status)
  const grid = document.getElementById("user-info-grid");
  grid.innerHTML = `
    <div class="info-item">
      <div class="info-label">User ID</div>
      <div class="info-value">#${user.id}</div>
    </div>
    <div class="info-item">
      <div class="info-label">Phone</div>
      <div class="info-value">${user.phone || "—"}</div>
    </div>
    <div class="info-item">
      <div class="info-label">Locked Status</div>
      <div class="info-value">${user.is_locked ? "🔴 Locked" : "🟢 Active"}</div>
    </div>
    <div class="info-item">
      <div class="info-label">Account Role</div>
      <div class="info-value" style="text-transform: capitalize;">${user.role}</div>
    </div>
  `;

  // Display the JWT token and Refresh Token
  document.getElementById("token-value").textContent = accessToken;
  document.getElementById("refresh-token-value").textContent = refreshToken || "N/A (Google Login / Session Stale)";

  // Enable Admin Management panel if admin
  const adminPanel = document.getElementById("admin-user-management");
  if (user.role === "admin" || user.role === "superadmin") {
    adminPanel.classList.remove("hidden");
    renderAdminPanel();
  } else {
    adminPanel.classList.add("hidden");
  }

  // Reset RBAC tester log
  document.getElementById("rbac-tester-logs").textContent = "Click a route above to test permissions...";
}

// ═════════════════════════════════════════════════
//  API CALL — REFRESH TOKEN (Rotation)
// ═════════════════════════════════════════════════
async function simulateTokenRefresh() {
  const refreshToken = sessionStorage.getItem("refresh_token");
  if (!refreshToken) {
    alert("No refresh token found. Please log in again.");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = await response.json();

    if (response.ok) {
      sessionStorage.setItem("access_token", data.access_token);
      sessionStorage.setItem("refresh_token", data.refresh_token);
      
      renderDashboard(data.user, data.access_token, data.refresh_token);
      alert("✅ Token rotated successfully!\nOld refresh token is now invalidated.");
    } else {
      alert("❌ Token refresh failed: " + (data.detail || "Your session may have expired."));
      logoutUser(false);
    }
  } catch (err) {
    console.error("Refresh error:", err);
    alert("Connection error during token refresh.");
  }
}

// ═════════════════════════════════════════════════
//  API CALL — FORGOT PASSWORD
// ═════════════════════════════════════════════════
async function forgotPassword(event) {
  event.preventDefault();

  const email = document.getElementById("forgot-email").value.trim();
  if (!email) {
    showToast("forgot-toast", "Please enter your email.", "error");
    return;
  }

  setLoading("forgot-btn", "forgot-spinner", true);

  try {
    const response = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await response.json();

    if (response.ok) {
      showToast("forgot-toast", "🎉 Success! Check the mock console log for your reset password link.", "success");
      document.getElementById("forgot-form").reset();
    } else {
      showToast("forgot-toast", data.detail || "Failed to process request.", "error");
    }
  } catch (err) {
    showToast("forgot-toast", "Cannot reach backend. Is FastAPI running?", "error");
  } finally {
    setLoading("forgot-btn", "forgot-spinner", false);
  }
}

// ═════════════════════════════════════════════════
//  API CALL — RESET PASSWORD
// ═════════════════════════════════════════════════
async function resetPassword(event) {
  event.preventDefault();

  const token = document.getElementById("reset-token-input").value;
  const new_password = document.getElementById("reset-password").value;

  if (!token || !new_password) {
    showToast("reset-toast", "Invalid reset code or password details.", "error");
    return;
  }

  setLoading("reset-btn", "reset-spinner", true);

  try {
    const response = await fetch(`${API_BASE}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password }),
    });

    const data = await response.json();

    if (response.ok) {
      showToast("reset-toast", "✅ Password reset successfully! Redirecting to login in 3s...", "success");
      document.getElementById("reset-form").reset();
      
      setTimeout(() => {
        // Clear url params
        window.history.replaceState({}, document.title, window.location.pathname);
        showTab("login");
      }, 3000);
    } else {
      showToast("reset-toast", data.detail || "Reset failed. The link may have expired.", "error");
    }
  } catch (err) {
    showToast("reset-toast", "Cannot reach server.", "error");
  } finally {
    setLoading("reset-btn", "reset-spinner", false);
  }
}

// ═════════════════════════════════════════════════
//  API CALL — CHANGE PASSWORD (Authenticated)
// ═════════════════════════════════════════════════
async function changePassword(event) {
  event.preventDefault();

  const current_password = document.getElementById("change-old-password").value;
  const new_password = document.getElementById("change-new-password").value;
  const token = sessionStorage.getItem("access_token");

  if (!current_password || !new_password) {
    showToast("change-password-toast", "Please fill in passwords.", "error");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/auth/change-password`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ current_password, new_password }),
    });

    const data = await response.json();

    if (response.ok) {
      showToast("change-password-toast", "✅ Password changed! All other sessions logged out.", "success");
      document.getElementById("change-password-form").reset();
    } else {
      showToast("change-password-toast", data.detail || "Failed to change password.", "error");
    }
  } catch (err) {
    showToast("change-password-toast", "Cannot connect to server.", "error");
  }
}

// ═════════════════════════════════════════════════
//  API CALL — LOGOUT
// ═════════════════════════════════════════════════
async function logoutUser(logoutEverywhere = false) {
  const refreshToken = sessionStorage.getItem("refresh_token");
  
  if (refreshToken) {
    try {
      await fetch(`${API_BASE}/auth/logout?logout_everywhere=${logoutEverywhere}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (e) {
      console.warn("Logout request failed:", e);
    }
  }

  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("refresh_token");
  sessionStorage.removeItem("user");
  showTab("login");
}

// ═════════════════════════════════════════════════
//  API CALL — EMAIL VERIFICATION
// ═════════════════════════════════════════════════
async function handleVerifyToken() {
  const params = new URLSearchParams(window.location.search);
  const token  = params.get("token");

  if (!token) return;

  showTab("verify");

  try {
    const response = await fetch(`${API_BASE}/auth/verify?token=${encodeURIComponent(token)}`);
    const data     = await response.json();

    const icon  = document.getElementById("verify-icon");
    const title = document.getElementById("verify-title");
    const msg   = document.getElementById("verify-msg");

    if (response.ok) {
      icon.textContent  = "✅";
      title.textContent = "Email verified!";
      msg.textContent   = data.message || "Your account is now active. You can log in.";
    } else {
      icon.textContent  = "❌";
      title.textContent = "Verification failed";
      msg.textContent   = data.detail || "The link may be expired or invalid.";
    }
  } catch (err) {
    document.getElementById("verify-icon").textContent  = "⚠️";
    document.getElementById("verify-title").textContent = "Network error";
    document.getElementById("verify-msg").textContent   = "Could not connect to the server.";
  }
}

// ═════════════════════════════════════════════════
//  RBAC TESTING
// ═════════════════════════════════════════════════
async function makeAuthorizedRequest(url, method = "GET") {
  const token = sessionStorage.getItem("access_token");
  const logBox = document.getElementById("rbac-tester-logs");

  logBox.textContent = `Sending ${method} ${url}...\n`;

  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });

    const status = response.status;
    const text = await response.text();
    let jsonFormatted = text;
    try {
      jsonFormatted = JSON.stringify(JSON.parse(text), null, 2);
    } catch {}

    logBox.textContent = `Status: ${status}\nResponse:\n${jsonFormatted}`;
  } catch (err) {
    logBox.textContent = `Network error calling ${url}: ${err.message}`;
  }
}

function testSellerRoute() {
  makeAuthorizedRequest(`${API_BASE}/seller/dashboard`);
}

function testSellerModify(ownerId) {
  makeAuthorizedRequest(`${API_BASE}/seller/products/${ownerId}/modify`);
}

function testAdminRoute() {
  makeAuthorizedRequest(`${API_BASE}/admin/users`);
}

// ═════════════════════════════════════════════════
//  ADMIN PANEL CONTROLS
// ═════════════════════════════════════════════════
async function renderAdminPanel() {
  const container = document.getElementById("admin-users-container");
  const token = sessionStorage.getItem("access_token");

  try {
    const response = await fetch(`${API_BASE}/admin/users`, {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!response.ok) {
      container.innerHTML = `<span style="color:#f87171;">Failed to fetch users: status ${response.status}</span>`;
      return;
    }

    const users = await response.json();

    let html = `
      <table style="width:100%; border-collapse:collapse; font-size:0.85rem; margin-top:0.5rem;">
        <thead>
          <tr style="border-bottom:1px solid var(--border); text-align:left; color:var(--text-muted);">
            <th style="padding:0.4rem;">ID</th>
            <th style="padding:0.4rem;">Email</th>
            <th style="padding:0.4rem;">Role</th>
            <th style="padding:0.4rem;">Verified</th>
            <th style="padding:0.4rem;">Status</th>
            <th style="padding:0.4rem; text-align:center;">Action</th>
          </tr>
        </thead>
        <tbody>
    `;

    users.forEach(u => {
      const statusText = u.is_locked ? "🔴 Locked" : "🟢 Active";
      const actionButton = u.is_locked 
        ? `<button class="btn-outline" style="padding:0.2rem 0.5rem; font-size:0.75rem; border-color:#34d399; color:#34d399;" onclick="unlockAdminUser(${u.id})">Unlock</button>`
        : `<button class="btn-outline" style="padding:0.2rem 0.5rem; font-size:0.75rem; border-color:#f87171; color:#f87171;" onclick="lockAdminUser(${u.id})">Lock</button>`;

      html += `
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
          <td style="padding:0.4rem;">#${u.id}</td>
          <td style="padding:0.4rem; max-width:120px; overflow:hidden; text-overflow:ellipsis;">${u.email}</td>
          <td style="padding:0.4rem; text-transform:capitalize;">${u.role}</td>
          <td style="padding:0.4rem;">${u.is_verified ? "Yes" : "No"}</td>
          <td style="padding:0.4rem;">${statusText}</td>
          <td style="padding:0.4rem; text-align:center;">${actionButton}</td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `<span style="color:#f87171;">Connection error.</span>`;
  }
}

async function lockAdminUser(userId) {
  const token = sessionStorage.getItem("access_token");
  try {
    const response = await fetch(`${API_BASE}/admin/users/${userId}/lock`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (response.ok) {
      renderAdminPanel();
    } else {
      alert("Failed to lock user.");
    }
  } catch (err) {
    console.error(err);
  }
}

async function unlockAdminUser(userId) {
  const token = sessionStorage.getItem("access_token");
  try {
    const response = await fetch(`${API_BASE}/admin/users/${userId}/unlock`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (response.ok) {
      renderAdminPanel();
    } else {
      alert("Failed to unlock user.");
    }
  } catch (err) {
    console.error(err);
  }
}

// ─────────────────────────────────────────────────
//  PAGE INITIALISATION
// ─────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  
  // 1. Check for verification token in URL
  if (params.get("token")) {
    handleVerifyToken();
    return;
  }

  // 2. Check for forgot password reset_token in URL
  if (params.get("reset_token")) {
    const resetToken = params.get("reset_token");
    showTab("reset");
    document.getElementById("reset-token-input").value = resetToken;
    return;
  }

  // 3. Auto-login session recovery
  const savedToken = sessionStorage.getItem("access_token");
  const savedRefreshToken = sessionStorage.getItem("refresh_token");
  const savedUser  = sessionStorage.getItem("user");
  
  if (savedToken && savedUser) {
    try {
      const user = JSON.parse(savedUser);
      renderDashboard(user, savedToken, savedRefreshToken);
      showTab("dashboard");
    } catch {
      sessionStorage.clear();
      showTab("register");
    }
    return;
  }

  showTab("register");
});
