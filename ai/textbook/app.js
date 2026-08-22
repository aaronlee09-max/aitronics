const KEY = "ai-textbook-kim-v1";

function load() {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); }
  catch { return {}; }
}
function save(data) {
  localStorage.setItem(KEY, JSON.stringify(data));
  updateProgress();
}

function collect() {
  const data = load();
  document.querySelectorAll("[data-field]").forEach((el) => {
    data[el.dataset.field] = el.type === "checkbox" ? el.checked : el.value;
  });
  save(data);
}

function restore() {
  const data = load();
  document.querySelectorAll("[data-field]").forEach((el) => {
    if (!(el.dataset.field in data)) return;
    if (el.type === "checkbox") el.checked = !!data[el.dataset.field];
    else el.value = data[el.dataset.field] || "";
  });
}

function show(id) {
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === id));
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === id));
  location.hash = id;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateProgress() {
  const data = load();
  const fields = [...document.querySelectorAll("[data-field]")];
  const filled = fields.filter((el) => {
    const v = data[el.dataset.field];
    return el.type === "checkbox" ? v : String(v || "").trim().length > 0;
  }).length;
  const pct = fields.length ? Math.round((filled / fields.length) * 100) : 0;
  const bar = document.querySelector(".bar span");
  const label = document.querySelector("[data-progress]");
  if (bar) bar.style.width = pct + "%";
  if (label) label.textContent = `작성 ${pct}%`;
}

function download() {
  collect();
  const blob = new Blob([JSON.stringify(load(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "인공지능기초_활동기록.json";
  a.click();
}

function printPage() {
  collect();
  window.print();
}

function resetAll() {
  if (!confirm("작성한 내용을 모두 지울까요?")) return;
  localStorage.removeItem(KEY);
  document.querySelectorAll("[data-field]").forEach((el) => {
    if (el.type === "checkbox") el.checked = false;
    else el.value = "";
  });
  updateProgress();
}

document.addEventListener("input", (e) => {
  if (e.target.matches("[data-field]")) collect();
});
document.addEventListener("change", (e) => {
  if (e.target.matches("[data-field]")) collect();
});

window.addEventListener("hashchange", () => {
  const id = location.hash.replace("#", "") || "cover";
  if (document.getElementById(id)) show(id);
});

document.addEventListener("DOMContentLoaded", () => {
  restore();
  const start = location.hash.replace("#", "") || "cover";
  show(document.getElementById(start) ? start : "cover");
  updateProgress();
});

document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-choice]");
  if (!btn) return;
  const group = btn.closest(".quiz");
  if (!group) return;
  group.querySelectorAll("[data-choice]").forEach((b) => b.classList.remove("ok", "bad"));
  btn.classList.add(btn.dataset.choice === "ok" ? "ok" : "bad");
  const out = group.querySelector(".quiz-out");
  if (out) out.textContent = btn.dataset.msg || "";
});
