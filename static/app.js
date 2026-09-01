/* Imdaad SPA — vanilla JS, zero build step */
const API = "/api/v1";
let token = localStorage.getItem("imdaad_token") || null;
let user = JSON.parse(localStorage.getItem("imdaad_user") || "null");
let isRegister = false;

const $ = (id) => document.getElementById(id);

/* ---------- helpers ---------- */
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(API + path, { ...opts, headers });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    const detail = data && data.detail ? (Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail) : "Something went wrong";
    throw new Error(detail);
  }
  return data;
}

function toast(msg, isError = false) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.hidden = true), 3500);
}

function showView(name) {
  ["landing", "auth", "app"].forEach((v) => ($(`view-${v}`).hidden = v !== name));
  window.scrollTo({ top: 0 });
}

function setNav() {
  const nav = $("nav-auth");
  if (user) {
    nav.innerHTML = `<button class="btn ghost" id="btn-logout">Logout</button>`;
    $("btn-logout").onclick = () => {
      token = null; user = null;
      localStorage.removeItem("imdaad_token");
      localStorage.removeItem("imdaad_user");
      showView("landing"); loadPublic();
    };
  } else {
    nav.innerHTML = `<button class="btn ghost" id="btn-login">Login</button>
      <button class="btn primary" id="btn-register">Register</button>`;
    $("btn-login").onclick = () => openAuth(false);
    $("btn-register").onclick = () => openAuth(true);
  }
}

/* ---------- landing ---------- */
async function loadStats() {
  try {
    const s = await api("/stats");
    $("stat-donors").textContent = s.total_donors;
    $("stat-eligible").textContent = s.eligible_donors;
    $("stat-open").textContent = s.open_requests;
    $("stat-fulfilled").textContent = s.fulfilled_requests;
  } catch (_) {}
}

async function loadPublicRequests() {
  try {
    const reqs = await api("/requests", { headers: {} });
    const wrap = $("public-requests");
    $("public-requests-empty").hidden = reqs.length > 0;
    wrap.innerHTML = reqs.map(requestCard).join("") || "";
  } catch (_) {}
}

function requestCard(r, extraActions = "") {
  const urgencyCls = r.urgency === "emergency" ? "emergency" : r.urgency === "urgent" ? "urgent" : "normal";
  return `<div class="card">
    <div class="card-top">
      <h4>${escapeHtml(r.patient_name)}</h4>
      <span class="badge blood">${r.blood_group}</span>
    </div>
    <div class="meta">📍 ${escapeHtml(r.city)}${r.hospital ? " · 🏥 " + escapeHtml(r.hospital) : ""} · ${r.units} unit${r.units > 1 ? "s" : ""}</div>
    <div class="card-top">
      <span class="badge ${urgencyCls}">${r.urgency}</span>
      <span class="badge status">${r.status}</span>
      <span class="offer-count">#${escapeHtml(r.request_number)}</span>
    </div>
    ${r.note ? `<div class="note">${escapeHtml(r.note)}</div>` : ""}
    <div class="card-actions">${extraActions}</div>
  </div>`;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------- compat engine UI ---------- */
function buildCompatPicker() {
  const groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
  $("compat-picker").innerHTML = groups
    .map((g) => `<button class="blood-chip" data-g="${g}">${g}</button>`)
    .join("");
  document.querySelectorAll(".blood-chip").forEach((chip) => {
    chip.onclick = () => {
      document.querySelectorAll(".blood-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      showCompat(chip.dataset.g);
    };
  });
}

function showCompat(recipient) {
  const table = {
    "A+": "A+, A-, O+, O-", "A-": "A-, O-",
    "B+": "B+, B-, O+, O-", "B-": "B-, O-",
    "AB+": "Everyone (A, B, AB, O — any Rh)", "AB-": "AB-, A-, B-, O-",
    "O+": "O+, O-", "O-": "O- only (universal donor)",
  };
  $("compat-result").innerHTML =
    `<p><strong>Patient ${recipient}</strong> can receive blood from: <span class="accent" style="color:var(--gold);font-weight:700">${table[recipient]}</span></p>
     <p class="muted">💡 ${recipient === "O-" ? "O- is the universal donor — every group can receive it." : recipient === "AB+" ? "AB+ is the universal recipient — can receive from everyone." : "Rh-negative donors can give to Rh-positive patients, never the reverse."}</p>`;
}

/* ---------- auth ---------- */
function openAuth(register) {
  isRegister = register;
  $("auth-title").textContent = register ? "Create an account" : "Login";
  $("auth-submit").textContent = register ? "Create account" : "Login";
  $("auth-toggle").textContent = register ? "Already have an account? Login" : "New here? Create an account";
  $("auth-role").hidden = !register;
  $("auth-name").hidden = !register;
  $("auth-phone").hidden = !register;
  $("auth-city").hidden = !register;
  $("auth-name").required = register;
  $("auth-phone").required = register;
  $("auth-city").required = register;
  $("auth-error").hidden = true;
  showView("auth");
}

$("auth-toggle").onclick = (e) => { e.preventDefault(); openAuth(!isRegister); };

$("auth-form").onsubmit = async (e) => {
  e.preventDefault();
  const err = $("auth-error");
  err.hidden = true;
  try {
    let data;
    if (isRegister) {
      data = await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: $("auth-email").value,
          password: $("auth-password").value,
          full_name: $("auth-name").value,
          phone: $("auth-phone").value,
          role: $("auth-role").value,
          city: $("auth-city").value,
        }),
      });
    } else {
      data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: $("auth-email").value, password: $("auth-password").value }),
      });
    }
    token = data.access_token;
    user = data.user;
    localStorage.setItem("imdaad_token", token);
    localStorage.setItem("imdaad_user", JSON.stringify(user));
    setNav();
    enterApp();
    toast(isRegister ? "Account created — welcome to Imdaad! 🩸" : "Welcome back!");
  } catch (ex) {
    err.textContent = ex.message;
    err.hidden = false;
  }
};

/* ---------- app ---------- */
function enterApp() {
  $("user-name").textContent = user.full_name.split(" ")[0];
  $("user-role").textContent = user.role;
  $("donor-panel").hidden = user.role === "requester";
  $("requester-panel").hidden = user.role === "donor";
  showView("app");
  if (user.role === "donor") { loadDonorProfile(); loadDonorRequests(); }
  if (user.role === "requester") { loadMyRequests(); }
  if (user.role === "admin") { toast("Admin view: use the API /docs for full control"); }
}

async function loadDonorProfile() {
  try {
    const p = await api("/donors/me");
    const view = $("donor-profile-view");
    view.innerHTML = `
      <p><strong>${p.blood_group}</strong> · ${p.eligible ? '<span style="color:var(--ok)">Eligible to donate ✅</span>' : '<span style="color:var(--warn)">Not eligible right now ⏳</span>'}</p>
      <p>${p.is_available ? "Available" : "Unavailable"} · ${p.donation_count} donation(s)${p.last_donation_date ? " · Last: " + new Date(p.last_donation_date).toLocaleDateString() : ""}</p>
      ${p.medical_notes ? `<p class="muted">${escapeHtml(p.medical_notes)}</p>` : ""}
      <div class="card-actions">
        <button class="btn outline" id="btn-edit-profile">Update profile</button>
        ${p.eligible ? `<button class="btn primary" id="btn-record-donation">Record a donation</button>` : ""}
      </div>`;
    $("btn-edit-profile").onclick = () => {
      $("donor-profile-form").hidden = false;
      $("dp-blood").value = p.blood_group;
      $("dp-available").checked = p.is_available;
      $("dp-notes").value = p.medical_notes || "";
    };
    const rd = $("btn-record-donation");
    if (rd) rd.onclick = async () => {
      try { await api("/donors/me/donate", { method: "POST" }); toast("Donation recorded — shukriya! ❤️"); loadDonorProfile(); loadDonorRequests(); } catch (ex) { toast(ex.message, true); }
    };
  } catch (_) {
    $("donor-profile-view").innerHTML = `<p class="muted">No profile yet.</p>`;
    $("donor-profile-form").hidden = false;
  }
}

$("donor-profile-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const exists = await api("/donors/me").catch(() => null);
    if (exists) {
      await api("/donors/me", { method: "PATCH", body: JSON.stringify({
        is_available: $("dp-available").checked,
        medical_notes: $("dp-notes").value,
      }) });
    } else {
      await api("/donors/profile", { method: "POST", body: JSON.stringify({
        blood_group: $("dp-blood").value,
        is_available: $("dp-available").checked,
        medical_notes: $("dp-notes").value,
      }) });
    }
    $("donor-profile-form").hidden = true;
    toast("Profile saved!");
    loadDonorProfile();
  } catch (ex) { toast(ex.message, true); }
};

async function loadDonorRequests() {
  try {
    const reqs = await api("/requests"); // open requests
    const wrap = $("donor-requests");
    wrap.innerHTML = reqs.map((r) => requestCard(r, `<button class="btn primary" data-offer="${r.id}">Offer to donate</button>`)).join("") || `<p class="muted">No open requests right now.</p>`;
    wrap.querySelectorAll("[data-offer]").forEach((b) => {
      b.onclick = async () => {
        try {
          await api(`/requests/${b.dataset.offer}/offers`, { method: "POST", body: JSON.stringify({ message: "I can donate — let me know the details." }) });
          toast("Offer sent! The requester will see it. 🤲");
          b.disabled = true; b.textContent = "Offered ✓";
        } catch (ex) { toast(ex.message, true); }
      };
    });
  } catch (_) {}
}

$("request-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const r = await api("/requests", { method: "POST", body: JSON.stringify({
      patient_name: $("rq-patient").value,
      blood_group: $("rq-blood").value,
      units: parseInt($("rq-units").value, 10),
      city: $("rq-city").value,
      hospital: $("rq-hospital").value || null,
      urgency: $("rq-urgency").value,
      note: $("rq-note").value,
    }) });
    toast(`Request posted — ${r.request_number} 🩸`);
    e.target.reset();
    loadMyRequests();
    loadStats();
  } catch (ex) { toast(ex.message, true); }
};

async function loadMyRequests() {
  try {
    const reqs = await api("/requests?mine=true");
    const wrap = $("my-requests");
    wrap.innerHTML = (await Promise.all(reqs.map(async (r) => {
      let offersHtml = "";
      try {
        const offers = await api(`/requests/${r.id}/offers`);
        offersHtml = offers.length
          ? `<div class="meta">${offers.map((o) => `<span>🩸 ${escapeHtml(o.donor_name)} (${o.blood_group}) — ${o.status}</span>`).join(" · ")}</div>
             <div class="card-actions">${offers.filter((o) => o.status === "pending").map((o) =>
               `<button class="btn primary" data-accept="${o.id}">Accept ${escapeHtml(o.donor_name)}</button>
                <button class="btn ghost" data-decline="${o.id}">Decline</button>`).join("")}
             </div>`
          : `<p class="muted">No offers yet.</p>`;
      } catch (_) {}
      const actions = r.status === "open"
        ? `<button class="btn outline" data-cancel="${r.id}">Cancel request</button>`
        : r.status === "matched"
        ? `<button class="btn primary" data-fulfill="${r.id}">Mark fulfilled ✅</button>`
        : "";
      return requestCard(r, actions + offersHtml);
    }))).join("");
    wrap.querySelectorAll("[data-cancel]").forEach((b) => b.onclick = async () => {
      try { await api(`/requests/${b.dataset.cancel}/cancel`, { method: "POST" }); toast("Request cancelled."); loadMyRequests(); } catch (ex) { toast(ex.message, true); }
    });
    wrap.querySelectorAll("[data-fulfill]").forEach((b) => b.onclick = async () => {
      try { await api(`/requests/${b.dataset.fulfill}/fulfill`, { method: "POST" }); toast("Request fulfilled — jazakAllah! ❤️"); loadMyRequests(); loadStats(); } catch (ex) { toast(ex.message, true); }
    });
    wrap.querySelectorAll("[data-accept]").forEach((b) => b.onclick = async () => {
      try { await api(`/offers/${b.dataset.accept}?action=accept`, { method: "PATCH" }); toast("Offer accepted — request matched!"); loadMyRequests(); } catch (ex) { toast(ex.message, true); }
    });
    wrap.querySelectorAll("[data-decline]").forEach((b) => b.onclick = async () => {
      try { await api(`/offers/${b.dataset.decline}?action=decline`, { method: "PATCH" }); toast("Offer declined."); loadMyRequests(); } catch (ex) { toast(ex.message, true); }
    });
  } catch (_) {}
}

/* ---------- boot ---------- */
$("btn-browse").onclick = () => {
  $("compat-panel").scrollIntoView({ behavior: "smooth" });
  document.querySelector(".requests-section").scrollIntoView({ behavior: "smooth" });
};
$("btn-register-donor").onclick = () => openAuth(true);

(async function boot() {
  setNav();
  buildCompatPicker();
  loadStats();
  loadPublicRequests();
  if (user && token) enterApp();
})();
