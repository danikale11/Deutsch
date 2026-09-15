"use strict";

/* ---------- Beallitasok / GitHub kapcsolat ---------- */

const DEFAULT_REPO = "danikale11/Deutsch";
const DEFAULT_BRANCH = "main";

const Settings = {
  get repo() { return localStorage.getItem("deutsch_repo") || DEFAULT_REPO; },
  get branch() { return localStorage.getItem("deutsch_branch") || DEFAULT_BRANCH; },
  get pat() { return localStorage.getItem("deutsch_pat") || ""; },
  save(repo, branch, pat) {
    localStorage.setItem("deutsch_repo", repo || DEFAULT_REPO);
    localStorage.setItem("deutsch_branch", branch || DEFAULT_BRANCH);
    if (pat) localStorage.setItem("deutsch_pat", pat);
  },
  clearToken() { localStorage.removeItem("deutsch_pat"); },
};

function utf8ToBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let binary = "";
  bytes.forEach((b) => { binary += String.fromCharCode(b); });
  return btoa(binary);
}

function base64ToUtf8(b64) {
  const binary = atob(b64.replace(/\n/g, ""));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

/* GitHub Contents API-n keresztuli olvasas: mindig friss, nem a Pages
   CDN-en at megy. PAT nelkul (meg publikus repo eseten is) mukodhet,
   csak alacsonyabb rate-limittel; ha nincs PAT es a hivas hibazik,
   visszaesunk a statikus relativ fetch-re. */
/* A frontend mindig a docs/ mappahoz kepest relativ utakkal dolgozik
   (pl. "data/daily/today.json"), mert a statikus fetch fallback is
   ehhez a mappahoz kepest ertelmezodik. A GitHub API-hoz viszont a
   teljes repo-relativ ut kell (a "docs/" elotaggal). */
function repoPath(webRelativePath) {
  return `docs/${webRelativePath}`;
}

async function githubGetFile(path) {
  const [owner, repo] = Settings.repo.split("/");
  const url = `https://api.github.com/repos/${owner}/${repo}/contents/${repoPath(path)}?ref=${encodeURIComponent(Settings.branch)}`;
  const headers = { Accept: "application/vnd.github+json" };
  if (Settings.pat) headers.Authorization = `Bearer ${Settings.pat}`;

  const res = await fetch(url, { headers });
  if (res.status === 404) return { exists: false, sha: null, data: null };
  if (!res.ok) throw new Error(`GitHub API hiba (${res.status}) ${path} olvasasakor`);
  const json = await res.json();
  const text = base64ToUtf8(json.content);
  return { exists: true, sha: json.sha, data: JSON.parse(text) };
}

async function githubPutFile(path, obj, message) {
  if (!Settings.pat) throw new Error("Nincs beallitva GitHub token a mentesehez.");
  const [owner, repo] = Settings.repo.split("/");
  const url = `https://api.github.com/repos/${owner}/${repo}/contents/${repoPath(path)}`;
  const headers = {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${Settings.pat}`,
    "Content-Type": "application/json",
  };

  const attemptPut = async () => {
    let sha = null;
    try {
      const current = await githubGetFile(path);
      sha = current.sha;
    } catch (_) { /* uj fajl, nincs meg sha */ }

    const body = {
      message,
      content: utf8ToBase64(JSON.stringify(obj, null, 2)),
      branch: Settings.branch,
    };
    if (sha) body.sha = sha;

    return fetch(url, { method: "PUT", headers, body: JSON.stringify(body) });
  };

  let res = await attemptPut();
  if (res.status === 409) {
    // valaki/valami kozben irt a fajlba: friss sha-val ujra probaljuk
    res = await attemptPut();
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Mentes sikertelen (${res.status}): ${detail}`);
  }
  return res.json();
}

/* Olvasas: elonyben a GitHub API (friss, PAT-tal auth-olt), ha nincs
   token vagy hibazik, statikus relativ fetch a Pages-rol (idobelyeg
   query paraméterrel a cache ellen). */
async function readDataFile(path) {
  if (Settings.pat) {
    try {
      const result = await githubGetFile(path);
      return result.exists ? result.data : null;
    } catch (err) {
      console.warn("GitHub API olvasas sikertelen, statikus fallback:", err);
    }
  }
  const res = await fetch(`${path}?t=${Date.now()}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Nem sikerult betolteni: ${path}`);
  return res.json();
}

/* ---------- Hasonlosag-alapu automatikus pontozasi javaslat ---------- */

function normalizeAnswer(str) {
  return (str || "")
    .toLowerCase()
    .normalize("NFKC")
    .replace(/[.,!?;:„”"'()\-]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function levenshtein(a, b) {
  const m = a.length, n = b.length;
  if (m === 0) return n;
  if (n === 0) return m;
  let prev = new Array(n + 1);
  let curr = new Array(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;
  for (let i = 1; i <= m; i++) {
    curr[0] = i;
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost);
    }
    [prev, curr] = [curr, prev];
  }
  return prev[n];
}

function similarityRatio(a, b) {
  const na = normalizeAnswer(a);
  const nb = normalizeAnswer(b);
  if (!na && !nb) return 1;
  if (!na || !nb) return 0;
  const dist = levenshtein(na, nb);
  const maxLen = Math.max(na.length, nb.length);
  return 1 - dist / maxLen;
}

function suggestTier(userAnswer, solution) {
  if (!userAnswer || !userAnswer.trim()) return "incorrect";
  const ratio = similarityRatio(userAnswer, solution);
  if (ratio >= 0.85) return "correct";
  if (ratio >= 0.5) return "partial";
  return "incorrect";
}

const TIER_POINTS = { correct: 1, partial: 0.5, incorrect: 0 };
const CATEGORY_LABELS = {
  hu_de_sentences: "Magyar → német mondatok",
  de_hu_sentences: "Német → magyar mondatok",
  hu_de_vocab: "Magyar → német szópárok",
  de_hu_vocab: "Német → magyar szópárok",
};
const CATEGORIES = Object.keys(CATEGORY_LABELS);

/* ---------- "Ma" ful: napi feladatsor ---------- */

const todayState = {
  date: null,
  tasks: null,
  checked: false,
};

function todayHistoryPath(dateStr) {
  return `data/history/${dateStr}.json`;
}

function renderTaskItem(container, task, category) {
  const tpl = document.getElementById("tpl-task-item");
  const node = tpl.content.cloneNode(true);
  const item = node.querySelector(".task-item");
  item.dataset.id = task.id;
  item.dataset.category = category;
  item.dataset.direction = task.direction;
  item.dataset.topic = task.topic || "";
  item.dataset.solution = task.solution;

  node.querySelector(".task-prompt").textContent = task.prompt;
  node.querySelector(".task-solution").textContent = `Megoldás: ${task.solution}`;
  const explanationText = task.explanation || task.note || "";
  const explanationEl = node.querySelector(".task-explanation");
  if (explanationText) {
    explanationEl.textContent = explanationText;
  } else {
    explanationEl.hidden = true;
  }

  const buttons = node.querySelectorAll(".tier-buttons button");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      item.dataset.tier = btn.dataset.tier;
    });
  });

  container.appendChild(node);
}

function renderTodayTasks(tasks) {
  const content = document.getElementById("today-content");
  content.innerHTML = "";

  for (const category of CATEGORIES) {
    const items = tasks[category] || [];
    if (!items.length) continue;
    const heading = document.createElement("h2");
    heading.textContent = CATEGORY_LABELS[category];
    content.appendChild(heading);
    for (const task of items) renderTaskItem(content, task, category);
  }

  const checkBtn = document.createElement("button");
  checkBtn.id = "check-all-btn";
  checkBtn.textContent = "Ellenőrzés";
  checkBtn.addEventListener("click", checkAllAnswers);
  content.appendChild(checkBtn);
}

function checkAllAnswers() {
  const items = document.querySelectorAll("#today-content .task-item");
  items.forEach((item) => {
    const input = item.querySelector(".task-input");
    const solution = item.dataset.solution;
    const userAnswer = input.value;
    input.disabled = true;

    const suggested = suggestTier(userAnswer, solution);
    item.dataset.tier = suggested;
    item.dataset.userAnswer = userAnswer;

    const reveal = item.querySelector(".task-reveal");
    reveal.hidden = false;
    const buttons = item.querySelectorAll(".tier-buttons button");
    buttons.forEach((btn) => {
      btn.classList.remove("suggested", "selected");
      if (btn.dataset.tier === suggested) {
        btn.classList.add("suggested", "selected");
      }
    });
  });

  document.getElementById("check-all-btn").remove();
  showSaveControls();
}

function collectAnswers() {
  const answers = {};
  for (const category of CATEGORIES) answers[category] = [];

  document.querySelectorAll("#today-content .task-item").forEach((item) => {
    const category = item.dataset.category;
    const tier = item.dataset.tier || "incorrect";
    answers[category].push({
      id: item.dataset.id,
      direction: item.dataset.direction,
      topic: item.dataset.topic || null,
      prompt: item.querySelector(".task-prompt").textContent,
      solution: item.dataset.solution,
      explanation: item.querySelector(".task-explanation").textContent || null,
      user_answer: item.dataset.userAnswer || "",
      tier,
      points: TIER_POINTS[tier],
    });
  });
  return answers;
}

function computeScore(answers) {
  let points = 0, max = 0;
  for (const category of CATEGORIES) {
    for (const a of answers[category]) {
      points += a.points;
      max += 1;
    }
  }
  return { points, max, percent: max ? Math.round((points / max) * 1000) / 10 : 0 };
}

function showSaveControls() {
  const content = document.getElementById("today-content");

  const summary = document.createElement("div");
  summary.className = "score-summary";
  summary.id = "score-summary";
  content.appendChild(summary);
  updateScoreSummary();

  document.querySelectorAll("#today-content .tier-buttons button").forEach((btn) => {
    btn.addEventListener("click", updateScoreSummary);
  });

  const saveBtn = document.createElement("button");
  saveBtn.id = "save-btn";
  saveBtn.textContent = "Eredmény mentése";
  saveBtn.addEventListener("click", saveTodayResult);
  content.appendChild(saveBtn);

  if (!Settings.pat) {
    const warn = document.createElement("div");
    warn.className = "hint";
    warn.textContent = "Nincs beállítva GitHub token — a mentéshez add meg a Beállítások fülön.";
    content.appendChild(warn);
  }
}

function updateScoreSummary() {
  const answers = collectAnswers();
  const score = computeScore(answers);
  const el = document.getElementById("score-summary");
  if (el) el.textContent = `Aktuális pontszám: ${score.points} / ${score.max} (${score.percent}%)`;
}

async function saveTodayResult() {
  const saveBtn = document.getElementById("save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Mentés folyamatban...";

  try {
    const answers = collectAnswers();
    const score = computeScore(answers);
    const dateStr = todayState.date;
    const path = todayHistoryPath(dateStr);

    let existing = null;
    try { existing = await githubGetFile(path); } catch (_) { /* ignore */ }
    const record = (existing && existing.exists) ? existing.data : { date: dateStr, attempts: [] };

    record.attempts.push({
      attempt_no: record.attempts.length + 1,
      timestamp: new Date().toISOString(),
      answers,
      score,
    });

    await githubPutFile(path, record, `Napi eredmény mentése: ${dateStr} (attempt ${record.attempts.length})`);

    saveBtn.textContent = "Elmentve ✓";
    showBanner(`Eredmény elmentve (${score.points}/${score.max} pont). Az előzmények lista rövidesen frissül.`, "ok");
  } catch (err) {
    saveBtn.disabled = false;
    saveBtn.textContent = "Eredmény mentése";
    showBanner(`Mentés sikertelen: ${err.message}`, "error");
  }
}

function showBanner(text, kind) {
  const banner = document.getElementById("today-banner");
  banner.textContent = text;
  banner.hidden = false;
  banner.style.background = kind === "ok" ? "#e8f3ea" : "#fdecea";
  banner.style.color = kind === "ok" ? "#1f5c30" : "#7a2b20";
  banner.style.borderColor = kind === "ok" ? "#bfe0c6" : "#f2b8ae";
}

async function loadToday() {
  const meta = document.getElementById("today-meta");
  const content = document.getElementById("today-content");
  content.textContent = "Betöltés...";

  try {
    const daily = await readDataFile("data/daily/today.json");
    if (!daily) {
      content.textContent = "Nincs még legenerálva a mai feladatsor.";
      return;
    }
    todayState.date = daily.date;
    todayState.tasks = daily.tasks;
    meta.textContent = `${daily.date} — legenerálva: ${new Date(daily.generated_at).toLocaleString("hu-HU")}`;
    renderTodayTasks(daily.tasks);
  } catch (err) {
    content.textContent = `Hiba a mai feladatsor betöltésekor: ${err.message}`;
  }
}

/* ---------- "Ujra csinalom" - egy korabbi nap ujra-gyakorlasa ---------- */

function loadTasksForRetry(dateStr, sourceAnswers) {
  const tasks = {};
  for (const category of CATEGORIES) {
    tasks[category] = (sourceAnswers[category] || []).map((a) => ({
      id: a.id,
      direction: a.direction,
      prompt: a.prompt,
      solution: a.solution,
      explanation: a.explanation,
      topic: a.topic,
    }));
  }
  todayState.date = dateStr;
  todayState.tasks = tasks;

  document.querySelector('.tab-btn[data-tab="today"]').click();
  document.getElementById("today-meta").textContent = `${dateStr} — újra próbálkozás`;
  renderTodayTasks(tasks);
  showBanner(`"${dateStr}" napi feladatait tölöttük be újra próbálkozásra. A mentés ehhez a naphoz kerül, új próbálkozásként.`, "ok");
}

/* ---------- "Elozmenyek" ful ---------- */

function renderHistoryStats(index) {
  const el = document.getElementById("history-stats");
  const tiles = [
    ["Sorozat", `${index.streak_days ?? 0} nap`],
    ["Gyakorolt napok", `${index.total_days_practiced ?? 0}`],
    ["Próbálkozások", `${index.total_attempts ?? 0}`],
    ["Átlag", index.average_percent != null ? `${Math.round(index.average_percent)}%` : "–"],
  ];
  el.innerHTML = "";
  for (const [label, value] of tiles) {
    const tile = document.createElement("div");
    tile.className = "stat-tile";
    tile.innerHTML = `<div class="value">${value}</div><div class="label">${label}</div>`;
    el.appendChild(tile);
  }
}

function renderHistoryList(index) {
  const listEl = document.getElementById("history-list");
  listEl.innerHTML = "";
  const days = index.days || [];
  if (!days.length) {
    listEl.innerHTML = '<p class="hint">Még nincs mentett napi eredmény.</p>';
    return;
  }
  for (const day of days) {
    const row = document.createElement("div");
    row.className = "history-day";
    const score = day.last_score || {};
    row.innerHTML = `
      <div>
        <div class="day-date">${day.date}</div>
        <div class="day-score">${day.attempt_count} próbálkozás</div>
      </div>
      <div class="day-score">${score.points ?? "?"} / ${score.max ?? "?"} (${score.percent ?? "?"}%)</div>
    `;
    row.addEventListener("click", () => showHistoryDetail(day.date));
    listEl.appendChild(row);
  }
}

async function showHistoryDetail(dateStr) {
  const detailEl = document.getElementById("history-detail");
  detailEl.textContent = "Betöltés...";
  try {
    const record = await readDataFile(todayHistoryPath(dateStr));
    if (!record) {
      detailEl.textContent = "Nem található részlet ehhez a naphoz.";
      return;
    }
    const lastAttempt = record.attempts[record.attempts.length - 1];
    detailEl.innerHTML = "";

    const heading = document.createElement("h2");
    heading.textContent = `${dateStr} részletei (${record.attempts.length}. próbálkozás megjelenítve az utolsóból)`;
    detailEl.appendChild(heading);

    for (const category of CATEGORIES) {
      const items = lastAttempt.answers[category] || [];
      if (!items.length) continue;
      const catHeading = document.createElement("h2");
      catHeading.textContent = CATEGORY_LABELS[category];
      detailEl.appendChild(catHeading);
      for (const a of items) {
        const div = document.createElement("div");
        div.className = "task-item";
        div.innerHTML = `
          <div class="task-prompt">${a.prompt}</div>
          <div class="hint">Válaszod: ${a.user_answer || "(üres)"}</div>
          <div class="task-solution">Megoldás: ${a.solution}</div>
          <div class="task-explanation">${a.explanation || ""}</div>
        `;
        detailEl.appendChild(div);
      }
    }

    const retryBtn = document.createElement("button");
    retryBtn.id = "retry-load-btn";
    retryBtn.textContent = "Újra csinálom";
    retryBtn.addEventListener("click", () => loadTasksForRetry(dateStr, lastAttempt.answers));
    detailEl.appendChild(retryBtn);
  } catch (err) {
    detailEl.textContent = `Hiba: ${err.message}`;
  }
}

async function loadHistory() {
  const listEl = document.getElementById("history-list");
  listEl.textContent = "Betöltés...";
  try {
    const index = await readDataFile("data/history_index.json");
    if (!index) {
      listEl.textContent = "Még nincs előzmény-index.";
      return;
    }
    renderHistoryStats(index);
    renderHistoryList(index);
  } catch (err) {
    listEl.textContent = `Hiba az előzmények betöltésekor: ${err.message}`;
  }
}

/* ---------- "Beallitasok" ful ---------- */

function initSettingsTab() {
  document.getElementById("settings-repo").value = Settings.repo;
  document.getElementById("settings-branch").value = Settings.branch;
  document.getElementById("settings-pat").value = Settings.pat;

  document.getElementById("settings-save").addEventListener("click", () => {
    const repo = document.getElementById("settings-repo").value.trim();
    const branch = document.getElementById("settings-branch").value.trim();
    const pat = document.getElementById("settings-pat").value.trim();
    Settings.save(repo, branch, pat);
    document.getElementById("settings-status").textContent = "Mentve.";
  });

  document.getElementById("settings-clear").addEventListener("click", () => {
    Settings.clearToken();
    document.getElementById("settings-pat").value = "";
    document.getElementById("settings-status").textContent = "Token törölve.";
  });
}

/* ---------- Fulek / inicializalas ---------- */

function initTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
      if (btn.dataset.tab === "history") loadHistory();
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initSettingsTab();
  loadToday();
});
