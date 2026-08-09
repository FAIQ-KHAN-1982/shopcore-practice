/* =====================================================
   app.js — ShopCore Modern Frontend Logic
===================================================== */

// Auto-detect base URL dynamically: if opened on localhost:8000/app, API base is relative/localhost:8000
const API_BASE = window.location.origin.includes(":8000")
  ? window.location.origin
  : "http://127.0.0.1:8000";

// Global cache for addresses
let cachedAddresses = [];

// ─────────────────────────────────────────────────
//  INITIALIZATION & ROUTING ON LOAD
// ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Check if URL has ?token=... (Email Verification)
  const urlParams = new URLSearchParams(window.location.search);
  const verifyToken = urlParams.get("token");

  if (verifyToken) {
    showTab("verify");
    handleVerifyToken(verifyToken);
    return;
  }

  // Check if user is already logged in
  const user = getStoredUser();
  const token = getAccessToken();

  if (user && token) {
    updateUserNavChip(user);
    renderDashboard(user, token, getRefreshToken());
    showTab("dashboard");
  } else {
    showTab("register");
  }
});

// ─────────────────────────────────────────────────
//  NAVIGATION & TAB SWITCHING
// ─────────────────────────────────────────────────
function showTab(name) {
  // Hide all panels
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
  // Deactivate nav tab buttons
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));

  // Show target panel
  const panel = document.getElementById("panel-" + name);
  if (panel) panel.classList.add("active");

  // Highlight matching tab button
  const btn = document.getElementById("tab-" + name);
  if (btn) btn.classList.add("active");

  // Control navbar tabs visibility
  const navTabs = document.getElementById("nav-tabs-container");
  const userChip = document.getElementById("user-chip");
  const token = getAccessToken();

  if (token) {
    if (navTabs) navTabs.style.display = "none";
    if (userChip) userChip.classList.remove("hidden");
  } else {
    if (navTabs) navTabs.style.display = "flex";
    if (userChip) userChip.classList.add("hidden");
  }

  // If navigating to addresses, fetch fresh address book data
  if (name === "addresses") {
    fetchAddresses();
  }
}

function navigateToDefault() {
  if (getAccessToken()) {
    showTab("dashboard");
  } else {
    showTab("register");
  }
}

// ─────────────────────────────────────────────────
//  STORAGE HELPERS
// ─────────────────────────────────────────────────
function getAccessToken() {
  return sessionStorage.getItem("access_token") || localStorage.getItem("access_token");
}

function getRefreshToken() {
  return sessionStorage.getItem("refresh_token") || localStorage.getItem("refresh_token");
}

function getStoredUser() {
  const raw = sessionStorage.getItem("user") || localStorage.getItem("user");
  try {
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function setSession(accessToken, refreshToken, user) {
  sessionStorage.setItem("access_token", accessToken);
  sessionStorage.setItem("refresh_token", refreshToken);
  sessionStorage.setItem("user", JSON.stringify(user));
  updateUserNavChip(user);
}

function clearSession() {
  sessionStorage.clear();
  localStorage.clear();
  cachedAddresses = [];
  const userChip = document.getElementById("user-chip");
  if (userChip) userChip.classList.add("hidden");
  showTab("login");
}

function updateUserNavChip(user) {
  const chip = document.getElementById("user-chip");
  const nameEl = document.getElementById("chip-user-name");
  const avatarEl = document.getElementById("chip-avatar-initials");

  if (!user || !chip) return;
  chip.classList.remove("hidden");

  const initials = ((user.first_name?.[0] || "") + (user.last_name?.[0] || "")).toUpperCase() || "U";
  if (avatarEl) avatarEl.textContent = initials;
  if (nameEl) nameEl.textContent = `${user.first_name || ""} ${user.last_name || ""}`.trim() || user.email;
}

// ─────────────────────────────────────────────────
//  AUTHORIZED FETCH WRAPPER
// ─────────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const token = getAccessToken();
  const headers = options.headers ? { ...options.headers } : {};

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  options.headers = headers;

  let response = await fetch(`${API_BASE}${endpoint}`, options);

  // Auto-refresh token if 401 Unauthorized occurs
  if (response.status === 401 && getRefreshToken()) {
    const refreshed = await attemptTokenRefresh();
    if (refreshed) {
      options.headers["Authorization"] = `Bearer ${getAccessToken()}`;
      response = await fetch(`${API_BASE}${endpoint}`, options);
    } else {
      clearSession();
      showToast("login-toast", "Session expired. Please log in again.", "error");
      throw new Error("Session expired");
    }
  }

  return response;
}

// ─────────────────────────────────────────────────
//  TOAST & UTILS
// ─────────────────────────────────────────────────
function showToast(id, message, type = "info") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = `toast ${type}`;
  el.classList.remove("hidden");

  setTimeout(() => {
    el.classList.add("hidden");
    el.className = "toast hidden";
  }, 5000);
}

function setLoading(btnId, spinnerId, loading) {
  const btn = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  if (!btn) return;
  btn.disabled = loading;
  if (spinner) {
    if (loading) spinner.classList.remove("hidden");
    else spinner.classList.add("hidden");
  }
}

function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "🙈";
  } else {
    input.type = "password";
    btn.textContent = "👁";
  }
}

function toggleSection(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("hidden");
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("hidden");
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("hidden");
}

// ─────────────────────────────────────────────────
//  PASSWORD STRENGTH CALCULATOR
// ─────────────────────────────────────────────────
function calculateStrength(password) {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[\W_]/.test(password)) score++;
  return score;
}

function updateStrengthBar(score, barId, labelId) {
  const bar = document.getElementById(barId);
  const label = document.getElementById(labelId);
  if (!bar || !label) return;

  const levels = [
    { pct: "0%", color: "transparent", text: "" },
    { pct: "25%", color: "#ef4444", text: "Weak" },
    { pct: "50%", color: "#f59e0b", text: "Fair" },
    { pct: "75%", color: "#38bdf8", text: "Good" },
    { pct: "100%", color: "#10b981", text: "Strong ✓" },
  ];

  const level = levels[score] || levels[0];
  bar.style.width = level.pct;
  bar.style.background = level.color;
  label.textContent = level.text;
  label.style.color = level.color;
}

function updateStrength(val) {
  updateStrengthBar(calculateStrength(val), "strength-bar", "strength-label");
}

function updateResetStrength(val) {
  updateStrengthBar(calculateStrength(val), "reset-strength-bar", "reset-strength-label");
}

// ═════════════════════════════════════════════════
//  AUTHENTICATION ACTIONS
// ═════════════════════════════════════════════════

// 1. REGISTER
async function registerUser(event) {
  event.preventDefault();

  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const first_name = document.getElementById("reg-first-name").value.trim();
  const last_name = document.getElementById("reg-last-name").value.trim();
  const phone = document.getElementById("reg-phone").value.trim() || null;
  const role = document.getElementById("reg-role").value;

  if (!email || !password || !first_name || !last_name) {
    showToast("register-toast", "Please fill in all required fields.", "error");
    return;
  }

  setLoading("register-btn", "reg-spinner", true);

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, first_name, last_name, phone, role }),
    });

    const data = await res.json();

    if (res.ok) {
      showToast(
        "register-toast",
        `🎉 Account created for ${data.first_name}! Check terminal/email for verification link.`,
        "success"
      );
      document.getElementById("register-form").reset();
      updateStrength("");
    } else {
      const errMsg = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail || "Registration failed.";
      showToast("register-toast", errMsg, "error");
    }
  } catch (err) {
    showToast("register-toast", "Cannot connect to server. Is FastAPI running?", "error");
  } finally {
    setLoading("register-btn", "reg-spinner", false);
  }
}

// 2. LOGIN
async function loginUser(event) {
  event.preventDefault();

  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  if (!email || !password) {
    showToast("login-toast", "Please enter your email and password.", "error");
    return;
  }

  setLoading("login-btn", "login-spinner", true);

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (res.ok) {
      setSession(data.access_token, data.refresh_token, data.user);
      renderDashboard(data.user, data.access_token, data.refresh_token);
      showTab("dashboard");
      document.getElementById("login-form").reset();
    } else {
      const errMsg = data.detail || "Login failed. Please check your credentials.";
      showToast("login-toast", errMsg, "error");
    }
  } catch (err) {
    showToast("login-toast", "Cannot connect to server. Is FastAPI running?", "error");
  } finally {
    setLoading("login-btn", "login-spinner", false);
  }
}

// 3. RESEND VERIFICATION TOKEN
async function resendVerificationToken(event) {
  event.preventDefault();

  const email = document.getElementById("resend-email").value.trim();
  if (!email) {
    showToast("resend-toast", "Please enter your email.", "error");
    return;
  }

  setLoading("resend-btn", "resend-spinner", true);

  try {
    const res = await fetch(`${API_BASE}/auth/resend_verfication_token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await res.json();

    if (res.ok) {
      showToast("resend-toast", data.message || "Verification email sent!", "success");
    } else {
      showToast("resend-toast", data.detail || "Failed to resend token.", "error");
    }
  } catch (err) {
    showToast("resend-toast", "Network error.", "error");
  } finally {
    setLoading("resend-btn", "resend-spinner", false);
  }
}

// 4. FORGOT PASSWORD
async function forgotPassword(event) {
  event.preventDefault();

  const email = document.getElementById("forgot-email").value.trim();
  if (!email) {
    showToast("forgot-toast", "Please enter your email.", "error");
    return;
  }

  setLoading("forgot-btn", "forgot-spinner", true);

  try {
    const res = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await res.json();

    if (res.ok) {
      showToast("forgot-toast", data.message, "success");
    } else {
      showToast("forgot-toast", data.detail || "Error requesting reset.", "error");
    }
  } catch (err) {
    showToast("forgot-toast", "Network error.", "error");
  } finally {
    setLoading("forgot-btn", "forgot-spinner", false);
  }
}

// 5. RESET PASSWORD
async function resetPassword(event) {
  event.preventDefault();

  const token = document.getElementById("reset-token-input").value.trim();
  const new_password = document.getElementById("reset-password").value;

  if (!token || !new_password) {
    showToast("reset-toast", "Please enter token and new password.", "error");
    return;
  }

  setLoading("reset-btn", "reset-spinner", true);

  try {
    const res = await fetch(`${API_BASE}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password }),
    });

    const data = await res.json();

    if (res.ok) {
      showToast("reset-toast", "Password reset successfully! You can now log in.", "success");
      setTimeout(() => showTab("login"), 2000);
    } else {
      showToast("reset-toast", data.detail || "Password reset failed.", "error");
    }
  } catch (err) {
    showToast("reset-toast", "Network error.", "error");
  } finally {
    setLoading("reset-btn", "reset-spinner", false);
  }
}

// 6. CHANGE PASSWORD
async function changePassword(event) {
  event.preventDefault();

  const current_password = document.getElementById("change-old-password").value;
  const new_password = document.getElementById("change-new-password").value;

  if (!current_password || !new_password) {
    showToast("change-password-toast", "Please fill in all password fields.", "error");
    return;
  }

  try {
    const res = await apiFetch("/auth/change-password", {
      method: "POST",
      body: { current_password, new_password },
    });

    const data = await res.json();

    if (res.ok) {
      showToast("change-password-toast", "Password updated successfully!", "success");
      document.getElementById("change-old-password").value = "";
      document.getElementById("change-new-password").value = "";
    } else {
      showToast("change-password-toast", data.detail || "Failed to change password.", "error");
    }
  } catch (err) {
    showToast("change-password-toast", "Error changing password.", "error");
  }
}

// 7. VERIFY EMAIL VIA LINK
async function handleVerifyToken(token) {
  const icon = document.getElementById("verify-icon");
  const title = document.getElementById("verify-title");
  const msg = document.getElementById("verify-msg");

  try {
    const res = await fetch(`${API_BASE}/auth/verify?token=${encodeURIComponent(token)}`);
    const data = await res.json();

    if (res.ok) {
      if (icon) icon.textContent = "✅";
      if (title) title.textContent = "Email Verified!";
      if (msg) msg.textContent = "Your account is verified. You can now sign in.";
    } else {
      if (icon) icon.textContent = "❌";
      if (title) title.textContent = "Verification Failed";
      if (msg) msg.textContent = data.detail || "Invalid or expired verification link.";
    }
  } catch (err) {
    if (icon) icon.textContent = "⚠️";
    if (title) title.textContent = "Connection Error";
    if (msg) msg.textContent = "Could not reach the server.";
  }
}

// 8. REFRESH TOKEN ROTATION
async function attemptTokenRefresh() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (res.ok) {
      const data = await res.json();
      setSession(data.access_token, data.refresh_token, data.user);
      renderDashboard(data.user, data.access_token, data.refresh_token);
      return true;
    }
  } catch (e) {}

  return false;
}

async function simulateTokenRefresh() {
  const success = await attemptTokenRefresh();
  if (success) {
    alert("Token rotated successfully! New JWT access and refresh tokens have been issued.");
  } else {
    alert("Failed to rotate token. Please log in again.");
    clearSession();
  }
}

// 9. LOGOUT
async function logoutUser(everywhere = false) {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await fetch(`${API_BASE}/auth/logout?logout_everywhere=${everywhere}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (e) {}
  }
  clearSession();
}

// ═════════════════════════════════════════════════
//  PROFILE MANAGEMENT
// ═════════════════════════════════════════════════

function renderDashboard(user, accessToken, refreshToken) {
  const initials = ((user.first_name?.[0] || "") + (user.last_name?.[0] || "")).toUpperCase() || "U";
  const fullName = `${user.first_name || ""} ${user.last_name || ""}`.trim() || user.email;

  document.getElementById("user-avatar").textContent = initials;
  document.getElementById("dashboard-name").textContent = fullName;
  document.getElementById("dashboard-email").textContent = user.email;
  document.getElementById("info-id").textContent = `#${user.id}`;
  document.getElementById("info-phone").textContent = user.phone || "Not provided";

  // Verification badge
  const vBadge = document.getElementById("verify-badge");
  if (user.is_verified) {
    vBadge.textContent = "✓ Verified";
    vBadge.className = "badge verified";
  } else {
    vBadge.textContent = "⏳ Unverified";
    vBadge.className = "badge";
  }

  // Role badge
  const rBadge = document.getElementById("role-badge");
  if (rBadge) rBadge.textContent = user.role;

  // Tokens
  document.getElementById("token-value").textContent = accessToken || "--";
  document.getElementById("refresh-token-value").textContent = refreshToken || "--";

  // Fetch address count
  fetchAddresses();
}

function openEditProfileModal() {
  const user = getStoredUser();
  if (!user) return;
  document.getElementById("edit-first-name").value = user.first_name || "";
  document.getElementById("edit-last-name").value = user.last_name || "";
  document.getElementById("edit-phone").value = user.phone || "";
  openModal("modal-edit-profile");
}

async function updateProfile(event) {
  event.preventDefault();

  const first_name = document.getElementById("edit-first-name").value.trim();
  const last_name = document.getElementById("edit-last-name").value.trim();
  const phone = document.getElementById("edit-phone").value.trim() || null;

  try {
    const res = await apiFetch("/users/me", {
      method: "PUT",
      body: { first_name, last_name, phone },
    });

    const updatedUser = await res.json();

    if (res.ok) {
      setSession(getAccessToken(), getRefreshToken(), updatedUser);
      renderDashboard(updatedUser, getAccessToken(), getRefreshToken());
      closeModal("modal-edit-profile");
      alert("Profile updated successfully!");
    } else {
      alert(updatedUser.detail || "Failed to update profile.");
    }
  } catch (err) {
    alert("Network error updating profile.");
  }
}

function openDeleteAccountModal() {
  openModal("modal-delete-account");
}

async function confirmDeleteAccount() {
  try {
    const res = await apiFetch("/users/me", { method: "DELETE" });
    if (res.ok) {
      closeModal("modal-delete-account");
      alert("Your account has been deleted.");
      clearSession();
    } else {
      const data = await res.json();
      alert(data.detail || "Failed to delete account.");
    }
  } catch (err) {
    alert("Error deleting account.");
  }
}

// ═════════════════════════════════════════════════
//  ADDRESS BOOK MANAGEMENT
// ═════════════════════════════════════════════════

async function fetchAddresses() {
  const token = getAccessToken();
  if (!token) return;

  try {
    const res = await apiFetch("/users/me/addresses", { method: "GET" });
    if (res.ok) {
      cachedAddresses = await res.json();
      renderAddressGrid(cachedAddresses);
      const countEl = document.getElementById("address-count-badge");
      if (countEl) countEl.textContent = cachedAddresses.length;
    }
  } catch (e) {}
}

function renderAddressGrid(addresses) {
  const container = document.getElementById("addresses-container");
  if (!container) return;

  if (!addresses || addresses.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--text-muted);">
        No saved addresses found. Click <strong>+ Add Address</strong> to create your first address.
      </div>
    `;
    return;
  }

  container.innerHTML = addresses
    .map((addr) => {
      const isDefault = addr.default;
      const addrName = addr.full_name || addr.Name || "Address";
      const addrLine = addr.address_line_1 || addr.address || "";

      return `
        <div class="address-card ${isDefault ? "is-default" : ""}">
          <div>
            <div class="address-name">
              ${escapeHtml(addrName)}
              ${isDefault ? '<span class="default-tag">Default</span>' : ""}
            </div>
            <div class="address-line">${escapeHtml(addrLine)}</div>
            <div class="address-line">${escapeHtml(addr.city)}</div>
            <div class="address-phone">📞 ${escapeHtml(addr.phone)}</div>
          </div>
          <div class="address-actions">
            ${
              !isDefault && addr.id
                ? `<button class="btn-secondary btn-xs" onclick="setDefaultAddress(${addr.id})">Make Default</button>`
                : ""
            }
            ${
              addr.id
                ? `<button class="btn-secondary btn-xs" onclick="openEditAddressModal(${addr.id})">Edit</button>
                   <button class="btn-danger btn-xs" onclick="deleteAddress(${addr.id})">Delete</button>`
                : ""
            }
          </div>
        </div>
      `;
    })
    .join("");
}

function openAddAddressModal() {
  if (cachedAddresses.length >= 10) {
    alert("You can only have a maximum of 10 addresses.");
    return;
  }
  document.getElementById("addr-full-name").value = "";
  document.getElementById("addr-phone").value = "";
  document.getElementById("addr-line1").value = "";
  document.getElementById("addr-city").value = "";
  openModal("modal-add-address");
}

async function saveAddress(event) {
  event.preventDefault();

  const full_name = document.getElementById("addr-full-name").value.trim();
  const phone = document.getElementById("addr-phone").value.trim();
  const address_line_1 = document.getElementById("addr-line1").value.trim();
  const city = document.getElementById("addr-city").value.trim();

  try {
    const res = await apiFetch("/users/me/addresses", {
      method: "POST",
      body: { full_name, phone, address_line_1, city },
    });

    const data = await res.json();

    if (res.ok) {
      closeModal("modal-add-address");
      fetchAddresses();
    } else {
      alert(data.detail || "Failed to add address.");
    }
  } catch (err) {
    alert("Error adding address.");
  }
}

function openEditAddressModal(addressId) {
  const addr = cachedAddresses.find((a) => a.id === addressId);
  if (!addr) return;

  document.getElementById("edit-addr-id").value = addr.id;
  document.getElementById("edit-addr-full-name").value = addr.full_name || addr.Name || "";
  document.getElementById("edit-addr-phone").value = addr.phone || "";
  document.getElementById("edit-addr-line1").value = addr.address_line_1 || addr.address || "";
  document.getElementById("edit-addr-city").value = addr.city || "";

  openModal("modal-edit-address");
}

async function submitEditAddress(event) {
  event.preventDefault();

  const addressId = document.getElementById("edit-addr-id").value;
  const full_name = document.getElementById("edit-addr-full-name").value.trim();
  const phone = document.getElementById("edit-addr-phone").value.trim();
  const address_line_1 = document.getElementById("edit-addr-line1").value.trim();
  const city = document.getElementById("edit-addr-city").value.trim();

  try {
    const res = await apiFetch(`/users/me/addresses/${addressId}`, {
      method: "PUT",
      body: { full_name, phone, address_line_1, city },
    });

    if (res.ok) {
      closeModal("modal-edit-address");
      fetchAddresses();
    } else {
      const data = await res.json();
      alert(data.detail || "Failed to update address.");
    }
  } catch (err) {
    alert("Error updating address.");
  }
}

async function deleteAddress(addressId) {
  if (!confirm("Are you sure you want to delete this address?")) return;

  try {
    const res = await apiFetch(`/users/me/addresses/${addressId}`, {
      method: "DELETE",
    });

    if (res.ok) {
      fetchAddresses();
    } else {
      const data = await res.json();
      alert(data.detail || "Failed to delete address.");
    }
  } catch (err) {
    alert("Error deleting address.");
  }
}

async function setDefaultAddress(addressId) {
  try {
    const res = await apiFetch(`/users/me/addresses/${addressId}/default`, {
      method: "PUT",
      body: { default: true },
    });

    if (res.ok) {
      fetchAddresses();
    } else {
      const data = await res.json();
      alert(data.detail || "Failed to set default address.");
    }
  } catch (err) {
    alert("Error setting default address.");
  }
}

// XSS SANITIZATION
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
