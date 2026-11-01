// Frontend logic. All model output is inserted with textContent (never innerHTML) to stay XSS-safe.
const $ = (id) => document.getElementById(id);
let current = null;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function showError(msg) {
  $("error").textContent = msg || "";
  $("error").hidden = !msg;
}

function render(story) {
  current = story;
  $("r-title").textContent = story.title;
  const box = $("r-story");
  box.replaceChildren();
  story.story.split(/\n\s*\n/).forEach((para) => {
    const p = document.createElement("p");
    p.textContent = para.trim();
    box.appendChild(p);
  });
  $("r-key").textContent = story.key_idea;
  const ol = $("r-questions");
  ol.replaceChildren();
  story.questions.forEach((q) => {
    const li = document.createElement("li");
    li.textContent = q;
    ol.appendChild(li);
  });
  const r = story.readability;
  $("r-meta").textContent =
    `${story.level_label} · ${r.word_count} words (target ${r.target_words}) · ` +
    `avg sentence ${r.avg_sentence_length} (target ≤ ${r.target_avg_sentence}) · grade ≈ ${r.grade_estimate}`;
  const warn = $("r-warn");
  warn.hidden = story.safety.passed;
  if (!story.safety.passed) {
    warn.textContent = "⚠️ Safety check flagged this story. A teacher should review it. " + (story.safety.note || "");
  }
  $("result").hidden = false;
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

function storyToText(s) {
  const qs = s.questions.map((q, i) => `${i + 1}. ${q}`).join("\n");
  return `${s.title}\n${"=".repeat(s.title.length)}\n\n${s.story}\n\nKEY IDEA\n${s.key_idea}\n\nQUESTIONS\n${qs}\n`;
}

async function loadSaved() {
  const list = $("saved-list");
  const rows = await api("/api/stories");
  list.replaceChildren();
  if (!rows.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "Nothing saved yet.";
    list.appendChild(li);
    return;
  }
  rows.forEach((row) => {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${row.title} — ${row.topic} (Grades ${row.level})`;
    const actions = document.createElement("div");
    actions.className = "li-actions";
    const open = document.createElement("button");
    open.className = "secondary";
    open.textContent = "Open";
    open.onclick = async () => render(await api(`/api/stories/${row.id}`));
    const del = document.createElement("button");
    del.className = "secondary";
    del.textContent = "Delete";
    del.onclick = async () => {
      await api(`/api/stories/${row.id}`, { method: "DELETE" });
      loadSaved();
    };
    actions.append(open, del);
    li.append(label, actions);
    list.appendChild(li);
  });
}

$("story-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError("");
  const btn = $("generate-btn");
  btn.disabled = true;
  btn.textContent = "Writing your story...";
  try {
    const story = await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({
        topic: $("topic").value,
        level: $("level").value,
        goal: $("goal").value,
        name: $("name").value,
        interest: $("interest").value,
        language: $("language").value,
      }),
    });
    render(story);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate story";
  }
});

$("save-btn").addEventListener("click", async () => {
  if (!current) return;
  try {
    await api("/api/stories", { method: "POST", body: JSON.stringify(current) });
    loadSaved();
  } catch (err) {
    showError(err.message);
  }
});

$("download-btn").addEventListener("click", () => {
  if (!current) return;
  const blob = new Blob([storyToText(current)], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = (current.title || "story").replace(/[^\w]+/g, "_") + ".txt";
  a.click();
  URL.revokeObjectURL(a.href);
});

$("print-btn").addEventListener("click", () => window.print());

(async function init() {
  const levels = await api("/api/levels");
  const sel = $("level");
  Object.entries(levels).forEach(([key, label]) => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = label;
    if (key === "3-5") opt.selected = true;
    sel.appendChild(opt);
  });
  loadSaved();
})();
