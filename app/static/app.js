// SimpleNotes frontend: plain JavaScript, no build step.

const $ = (id) => document.getElementById(id);

const state = {
  current: null, // note being viewed/edited (null = new note)
  query: "",
  tag: "",
};

// ---------- API ----------

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

const noteUrl = (title) => `/api/notes/${encodeURIComponent(title)}`;

// ---------- Rendering ----------

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderMarkdown(content) {
  // [[Note Title]] -> link to that note
  const withLinks = content.replace(
    /\[\[([^\]]+)\]\]/g,
    (_, title) => `[${title}](#/note/${encodeURIComponent(title.trim())})`,
  );
  return DOMPurify.sanitize(marked.parse(withLinks));
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 3000);
}

function show(section) {
  for (const id of ["empty", "viewer", "editor"]) $(id).hidden = id !== section;
}

async function loadList() {
  const params = new URLSearchParams({ q: state.query, tag: state.tag });
  const [notes, tags] = await Promise.all([
    api("GET", `/api/notes?${params}`),
    api("GET", "/api/tags"),
  ]);

  $("tags").innerHTML = tags
    .map(
      ({ tag, count }) =>
        `<button class="tag ${tag === state.tag ? "active" : ""}" data-tag="${escapeHtml(tag)}">#${escapeHtml(tag)} <small>${count}</small></button>`,
    )
    .join("");

  $("note-list").innerHTML = notes.length
    ? notes
        .map(
          (note) => `
          <li class="${note.title === state.current?.title ? "active" : ""}">
            <a href="#/note/${encodeURIComponent(note.title)}">
              <strong>${escapeHtml(note.title)}</strong>
              <span>${escapeHtml(note.snippet.slice(0, 60)) || "<em>Empty note</em>"}</span>
            </a>
          </li>`,
        )
        .join("")
    : `<li class="none">No notes found</li>`;
}

async function openNote(title) {
  try {
    const note = await api("GET", noteUrl(title));
    state.current = note;
    $("view-title").textContent = note.title;
    $("view-meta").textContent =
      "Last modified: " + new Date(note.modified).toLocaleString();
    $("view-body").innerHTML = renderMarkdown(note.content);
    show("viewer");
  } catch (err) {
    toast(err.message);
    state.current = null;
    show("empty");
  }
  loadList();
}

function openEditor(note) {
  state.current = note;
  $("edit-title").value = note ? note.title : "";
  $("edit-content").value = note ? note.content : "";
  $("edit-preview").innerHTML = renderMarkdown($("edit-content").value);
  show("editor");
  (note ? $("edit-content") : $("edit-title")).focus();
}

// ---------- Actions ----------

async function save() {
  const body = {
    title: $("edit-title").value,
    content: $("edit-content").value,
  };
  try {
    const saved = state.current
      ? await api("PUT", noteUrl(state.current.title), body)
      : await api("POST", "/api/notes", body);
    toast("Saved");
    const hash = `#/note/${encodeURIComponent(saved.title)}`;
    if (location.hash === hash) openNote(saved.title);
    else location.hash = hash;
  } catch (err) {
    toast(err.message);
  }
}

async function remove() {
  if (!confirm(`Delete "${state.current.title}"?`)) return;
  try {
    await api("DELETE", noteUrl(state.current.title));
    toast("Deleted");
    location.hash = "";
  } catch (err) {
    toast(err.message);
  }
}

function route() {
  const match = location.hash.match(/^#\/note\/(.+)$/);
  if (match) {
    openNote(decodeURIComponent(match[1]));
  } else {
    state.current = null;
    show("empty");
    loadList();
  }
}

// ---------- Events ----------

$("new-btn").onclick = () => openEditor(null);
$("edit-btn").onclick = () => openEditor(state.current);
$("delete-btn").onclick = remove;
$("save-btn").onclick = save;
$("cancel-btn").onclick = () =>
  state.current ? openNote(state.current.title) : show("empty");

$("edit-content").oninput = () => {
  $("edit-preview").innerHTML = renderMarkdown($("edit-content").value);
};

let searchTimer;
$("search").oninput = (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.query = e.target.value;
    loadList();
  }, 200);
};

$("tags").onclick = (e) => {
  const button = e.target.closest(".tag");
  if (!button) return;
  state.tag = state.tag === button.dataset.tag ? "" : button.dataset.tag;
  loadList();
};

document.addEventListener("keydown", (e) => {
  const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName);
  if (e.key === "/" && !typing) {
    e.preventDefault();
    $("search").focus();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "s" && !$("editor").hidden) {
    e.preventDefault();
    save();
  }
});

window.addEventListener("hashchange", route);
route();
