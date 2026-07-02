/* =====================================================
   app.js — ShopCore Frontend Logic
   Beginner-friendly, no frameworks, vanilla JS only.

   API ENDPOINTS USED:
   ┌──────────────────────────────────────────────────────┐
   │  POST  /auth/register   → registerUser()             │
   │  POST  /auth/login      → loginUser()                │
   │  GET   /auth/verify     → handleVerifyToken()        │
   └──────────────────────────────────────────────────────┘
===================================================== */

// ─────────────────────────────────────────────────
//  BASE URL — change this if your FastAPI runs on
//  a different host or port.
// ─────────────────────────────────────────────────
const API_BASE = "http://localhost:8000";

// ─────────────────────────────────────────────────
//  PANEL / TAB NAVIGATION
//  Hides all panels, then shows the requested one.
// ─────────────────────────────────────────────────
/**
 * showTab(name)
 * name: "register" | "login" | "dashboard" | "verify"
 */
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
}

// ─────────────────────────────────────────────────
//  SHOW TOAST  (success/error message under a form)
// ─────────────────────────────────────────────────
/**
 * showToast(id, message, type)
 * id   : element id of the toast div
 * type : "success" | "error"
 */
function showToast(id, message, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = "toast " + type;   // sets colour class
  el.classList.remove("hidden");

  // Auto-hide after 5 seconds
  setTimeout(() => {
    el.classList.add("hidden");
    el.className = "toast hidden";
  }, 5000);
}

// ─────────────────────────────────────────────────
//  TOGGLE PASSWORD VISIBILITY (the 👁 button)
// ─────────────────────────────────────────────────
/**
 * togglePassword(inputId, btn)
 * inputId : the id of the <input type="password">
 * btn     : the button element that was clicked
 */
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
//  Updates the coloured bar below the password field
//  as the user types.
// ─────────────────────────────────────────────────
/**
 * updateStrength(password)
 * Called by the oninput event on the register password field.
 */
function updateStrength(password) {
  const bar   = document.getElementById("strength-bar");
  const label = document.getElementById("strength-label");
  if (!bar || !label) return;

  let score = 0;
  if (password.length >= 8)          score++;   // length OK
  if (/[A-Z]/.test(password))        score++;   // has uppercase
  if (/[0-9]/.test(password))        score++;   // has digit
  if (/[\W_]/.test(password))        score++;   // has special char

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

// ─────────────────────────────────────────────────
//  SET LOADING STATE on a button
// ─────────────────────────────────────────────────
/**
 * setLoading(btnId, spinnerId, loading)
 * loading: true  → disable button, show spinner
 * loading: false → enable button, hide spinner
 */
function setLoading(btnId, spinnerId, loading) {
  const btn     = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  if (!btn || !spinner) return;

  btn.disabled = loading;
  if (loading) {
    spinner.classList.remove("hidden");
    btn.querySelector(".btn-text").style.opacity = "0.5";
  } else {
    spinner.classList.add("hidden");
    btn.querySelector(".btn-text").style.opacity = "1";
  }
}

// ═════════════════════════════════════════════════
//  API CALL 1 — REGISTER
//  Endpoint : POST /auth/register
//  Request  : { email, password, first_name, last_name, phone? }
//  Response : UserResponse (id, email, first_name, last_name, phone, is_verified)
// ═════════════════════════════════════════════════
async function registerUser(event) {
  // Prevent the default HTML form submission (page reload)
  event.preventDefault();

  // --- 1. Collect form values ---
  const email      = document.getElementById("reg-email").value.trim();
  const password   = document.getElementById("reg-password").value;
  const first_name = document.getElementById("reg-first-name").value.trim();
  const last_name  = document.getElementById("reg-last-name").value.trim();
  const phone      = document.getElementById("reg-phone").value.trim() || null;

  // --- 2. Basic client-side validation ---
  if (!email || !password || !first_name || !last_name) {
    showToast("register-toast", "Please fill in all required fields.", "error");
    return;
  }

  // --- 3. Show loading state ---
  setLoading("register-btn", "reg-spinner", true);

  try {
    // --- 4. Call the API ---
    //  URL    : POST http://localhost:8000/auth/register
    //  Body   : JSON with user details
    //  Returns: UserResponse on success, or 400/422 on error
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, first_name, last_name, phone }),
    });

    const data = await response.json();

    // --- 5. Handle the response ---
    if (response.ok) {
      // 201 Created — registration successful
      showToast(
        "register-toast",
        `🎉 Account created for ${data.first_name}! Check your email to verify your account.`,
        "success"
      );
      // Clear the form
      document.getElementById("register-form").reset();
      updateStrength(""); // reset strength bar
    } else {
      // 400 Bad Request — validation error or duplicate email
      const errMsg = data.detail || "Registration failed. Please try again.";
      showToast("register-toast", errMsg, "error");
    }
  } catch (err) {
    // Network error — server is probably not running
    showToast(
      "register-toast",
      "Cannot reach the server. Is FastAPI running on port 8000?",
      "error"
    );
    console.error("Register error:", err);
  } finally {
    // Always re-enable the button
    setLoading("register-btn", "reg-spinner", false);
  }
}

// ═════════════════════════════════════════════════
//  API CALL 2 — LOGIN
//  Endpoint : POST /auth/login
//  Request  : { email, password }
//  Response : LoginResponse { access_token, token_type, user: UserResponse }
// ═════════════════════════════════════════════════
async function loginUser(event) {
  event.preventDefault();

  // --- 1. Collect form values ---
  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  if (!email || !password) {
    showToast("login-toast", "Please enter your email and password.", "error");
    return;
  }

  // --- 2. Show loading ---
  setLoading("login-btn", "login-spinner", true);

  try {
    // --- 3. Call the API ---
    //  URL    : POST http://localhost:8000/auth/login
    //  Body   : JSON with email + password
    //  Returns: access_token + user object on success, 401 on wrong credentials
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    // --- 4. Handle response ---
    if (response.ok) {
      // Save the JWT token in sessionStorage
      // (sessionStorage is cleared when the browser tab is closed)
      sessionStorage.setItem("access_token", data.access_token);
      sessionStorage.setItem("user", JSON.stringify(data.user));

      // Show the dashboard with user info
      renderDashboard(data.user, data.access_token);
      showTab("dashboard");

      // Clear login form
      document.getElementById("login-form").reset();
    } else {
      // 401 Unauthorized — wrong email or password
      const errMsg = data.detail || "Login failed. Check your credentials.";
      showToast("login-toast", errMsg, "error");
    }
  } catch (err) {
    showToast(
      "login-toast",
      "Cannot reach the server. Is FastAPI running on port 8000?",
      "error"
    );
    console.error("Login error:", err);
  } finally {
    setLoading("login-btn", "login-spinner", false);
  }
}

// ─────────────────────────────────────────────────
//  RENDER DASHBOARD  (called after successful login)
//  Fills in all the user info fields.
// ─────────────────────────────────────────────────
/**
 * renderDashboard(user, token)
 * user  : UserResponse object from the API
 * token : JWT access_token string
 */
function renderDashboard(user, token) {
  // Initials for the avatar circle
  const initials =
    (user.first_name?.[0] || "") + (user.last_name?.[0] || "");
  document.getElementById("user-avatar").textContent = initials.toUpperCase();

  // Name & email
  document.getElementById("dashboard-name").textContent =
    `Hello, ${user.first_name}! 👋`;
  document.getElementById("dashboard-email").textContent = user.email;

  // Verification badge
  const badge = document.getElementById("verify-badge");
  if (user.is_verified) {
    badge.textContent = "✅ Verified";
    badge.classList.add("verified");
  } else {
    badge.textContent = "⏳ Email not verified";
    badge.classList.remove("verified");
  }

  // Info grid (id, phone, joined)
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
    <div class="info-item" style="grid-column:1/-1">
      <div class="info-label">Full Name</div>
      <div class="info-value">${user.first_name} ${user.last_name}</div>
    </div>
  `;

  // Display the JWT token (useful for beginners to see it)
  document.getElementById("token-value").textContent = token;
}

// ─────────────────────────────────────────────────
//  LOGOUT
// ─────────────────────────────────────────────────
function logoutUser() {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("user");
  showTab("login");
}

// ═════════════════════════════════════════════════
//  API CALL 3 — EMAIL VERIFICATION
//  Endpoint : GET /auth/verify?token=<JWT>
//  Request  : token passed as a query string parameter
//  Response : { message: "Email verified successfully" }
//
//  This is triggered automatically when the page loads
//  IF the URL contains ?token=... (from the email link).
// ═════════════════════════════════════════════════
async function handleVerifyToken() {
  // Extract the "token" value from the URL query string
  // e.g. http://localhost:8000/auth/verify?token=eyJ...
  // When the user opens this URL, the browser lands on our
  // index.html (served on a different port) but we still
  // read the token and call the FastAPI backend directly.
  const params = new URLSearchParams(window.location.search);
  const token  = params.get("token");

  if (!token) return;   // No token in URL — skip verification

  // Show the verify panel
  showTab("verify");

  try {
    // --- Call the API ---
    //  URL : GET http://localhost:8000/auth/verify?token=<token>
    //  No request body needed — token is in the query string.
    const response = await fetch(`${API_BASE}/auth/verify?token=${encodeURIComponent(token)}`);
    const data     = await response.json();

    const icon  = document.getElementById("verify-icon");
    const title = document.getElementById("verify-title");
    const msg   = document.getElementById("verify-msg");

    if (response.ok) {
      // Success
      icon.textContent  = "✅";
      title.textContent = "Email verified!";
      msg.textContent   = data.message || "Your account is now active. You can log in.";
    } else {
      // Error (expired token, already verified, etc.)
      icon.textContent  = "❌";
      title.textContent = "Verification failed";
      msg.textContent   = data.detail || "The link may be expired or invalid.";
    }
  } catch (err) {
    document.getElementById("verify-icon").textContent  = "⚠️";
    document.getElementById("verify-title").textContent = "Network error";
    document.getElementById("verify-msg").textContent   =
      "Could not connect to the server. Is FastAPI running?";
    console.error("Verify error:", err);
  }
}

// ─────────────────────────────────────────────────
//  PAGE INITIALISATION
//  Runs automatically when the page finishes loading.
// ─────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  // 1. Check if there's a verification token in the URL
  //    (user clicked the verification link from their email)
  const params = new URLSearchParams(window.location.search);
  if (params.get("token")) {
    handleVerifyToken();
    return;  // don't do anything else
  }

  // 2. If the user was already logged in (token in sessionStorage),
  //    skip the login screen and go straight to the dashboard.
  const savedToken = sessionStorage.getItem("access_token");
  const savedUser  = sessionStorage.getItem("user");
  if (savedToken && savedUser) {
    try {
      const user = JSON.parse(savedUser);
      renderDashboard(user, savedToken);
      showTab("dashboard");
    } catch {
      // Corrupted data — start fresh
      sessionStorage.clear();
    }
    return;
  }

  // 3. Default: show the register tab
  showTab("register");
});
