# SimpleNotes

A simple Markdown note-taking web app, inspired by [flatnotes](https://github.com/dullage/flatnotes).
There is no database: every note is a plain `.md` file in a folder on disk.

Group project for **DS600 Cloud Computing for Economics** (SMU). The app is deployed on the
AWS Academy Sandbox.

## Features

- Create, view, edit, rename and delete notes
- Markdown editor with live preview
- Full-text search across titles and content (press `/` to jump to the search box)
- Tags: write `#tag` anywhere in a note, then click the tag in the sidebar to filter
- Links between notes: write `[[Another Note Title]]`
- Optional username / password login (HTTP Basic Auth)
- `Ctrl+S` to save; works in dark mode and on mobile screens

## Tech Stack

| Part     | Technology                                                                 |
| -------- | -------------------------------------------------------------------------- |
| Backend  | Python 3.10+, FastAPI, Uvicorn                                             |
| Frontend | Plain HTML / CSS / JavaScript (marked.js for Markdown, DOMPurify for safety) |
| Storage  | Markdown files on the local file system                                    |
| Hosting  | AWS EC2 (deployed with CloudFormation)                                     |

## Project Structure

```
simplenotes/
├── app/
│   ├── main.py          # Backend: API routes, file storage, optional login
│   └── static/          # Frontend: the web page the user sees
│       ├── index.html   # Page layout (sidebar, viewer, editor)
│       ├── app.js       # Page logic: calls the API and updates the page
│       └── style.css    # Styling
├── data/                # Notes are saved here (created automatically, not in Git)
├── requirements.txt     # Python packages
└── README.md
```

## Installation (run locally)

You need **Python 3.10 or newer** (the code uses the `str | None` syntax).
Check your version first:

```bash
python --version
```

**Step 1 — Get the code**

```bash
git clone https://github.com/<your-username>/simplenotes.git
cd simplenotes
```

**Step 2 — Create and activate a virtual environment**

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Step 3 — Install the packages**

```bash
pip install -r requirements.txt
```

**Step 4 — Start the app**

```bash
uvicorn app.main:app --reload --port 8080
```

**Step 5 — Open it**

Go to http://localhost:8080 in your browser. Create a note, then check that a new `.md` file
appears in the `data/` folder.

## Configuration (environment variables)

| Variable       | Default | Meaning                                              |
| -------------- | ------- | ---------------------------------------------------- |
| `NOTES_DIR`    | `data`  | Folder where notes are stored                        |
| `APP_USERNAME` | `admin` | Login username                                       |
| `APP_PASSWORD` | (empty) | Login password. **If empty, no login is required.**  |

## API

| Method | Path                            | Description                                     |
| ------ | ------------------------------- | ----------------------------------------------- |
| GET    | `/api/notes?q=word&tag=name`    | List notes (optionally search / filter by tag)  |
| GET    | `/api/notes/{title}`            | Get one note                                    |
| POST   | `/api/notes`                    | Create a note: `{"title": "...", "content": "..."}` |
| PUT    | `/api/notes/{title}`            | Update or rename a note                         |
| DELETE | `/api/notes/{title}`            | Delete a note                                   |
| GET    | `/api/tags`                     | List all tags with counts                       |
| GET    | `/health`                       | Health check (returns `{"status": "ok"}`)       |

Interactive API docs are available at `/docs` while the app is running.

## Code Walkthrough

The app has two halves that talk to each other over HTTP:

- **Frontend** (`app/static/`) — runs in the user's browser.
- **Backend** (`app/main.py`) — runs on the server (your laptop or the EC2 instance).

### Backend: `app/main.py`

| Section     | What it does                                                                 |
| ----------- | ---------------------------------------------------------------------------- |
| Settings    | Reads `NOTES_DIR`, `APP_USERNAME`, `APP_PASSWORD` and creates the notes folder |
| Auth        | `basic_auth` middleware: if a password is set, every request must log in    |
| Helpers     | `clean_title` blocks unsafe titles, `note_path` turns a title into a file path, `get_tags` finds `#tags`, `note_info` builds the summary shown in the list |
| API         | One function per route in the API table above                               |
| Frontend    | `/` returns `index.html`; `/static/...` serves the CSS and JS files          |

### Frontend: `app/static/app.js`

| Function      | What it does                                                   |
| ------------- | -------------------------------------------------------------- |
| `api()`       | Sends a request to the backend and returns the JSON reply      |
| `loadList()`  | Fetches notes and tags, then draws the sidebar                 |
| `openNote()`  | Fetches one note and shows it, rendered as Markdown            |
| `openEditor()`| Shows the editor with live preview                             |
| `save()` / `remove()` | Create / update / delete a note                        |
| `route()`     | Reads the URL (e.g. `#/note/Hello`) to decide what to show     |

### Example: what happens when you click "Save"

1. **Browser** — `save()` in `app.js` reads the title and content from the editor.
2. **Browser → Server** — it sends `POST /api/notes` (new note) or `PUT /api/notes/{title}`
   (existing note) with the data as JSON.
3. **Server** — FastAPI calls `create_note()` or `update_note()` in `main.py`.
   The data is checked by the `NoteIn` model, and `note_path()` turns the title into a safe
   file path such as `data/Hello.md`.
4. **Server** — the content is written to that `.md` file (`path.write_text(...)`).
   If the title changed, the old file is renamed first.
5. **Server → Browser** — the server replies with the saved note. The browser shows a
   "Saved" message, opens the note and refreshes the sidebar list.

Reading, searching and deleting follow the same pattern: browser → API route → file on disk → reply.

## Deploy to AWS (CloudFormation)

_To be completed._ The CloudFormation template will live in `scripts/`. It creates the VPC
network and an EC2 instance, and its user data clones this repository, installs the
requirements in a virtual environment and starts the app on port 8080.

## Credits

Inspired by [flatnotes](https://github.com/dullage/flatnotes) by Dullage.
