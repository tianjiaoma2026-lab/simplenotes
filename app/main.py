"""SimpleNotes: a tiny, database-less note app inspired by flatnotes.

Every note is a plain Markdown file in NOTES_DIR. The file name (without
.md) is the note title. Tags are words starting with "#" inside the note.
"""

import base64
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

NOTES_DIR = Path(os.environ.get("NOTES_DIR", "data")).resolve()
NOTES_DIR.mkdir(parents=True, exist_ok=True)

# Optional login. If APP_PASSWORD is empty, the app is open to everyone.
APP_USERNAME = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

STATIC_DIR = Path(__file__).parent / "static"
INVALID_TITLE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
TAG_PATTERN = re.compile(r"(?<!\S)#([\w-]+)")

app = FastAPI(title="SimpleNotes")


# ---------- Auth ----------


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    if not APP_PASSWORD or request.url.path == "/health":
        return await call_next(request)
    header = request.headers.get("Authorization", "")
    if header.startswith("Basic "):
        try:
            decoded = base64.b64decode(header[6:]).decode()
            username, _, password = decoded.partition(":")
            if secrets.compare_digest(
                username, APP_USERNAME
            ) and secrets.compare_digest(password, APP_PASSWORD):
                return await call_next(request)
        except (ValueError, UnicodeDecodeError):
            pass
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="SimpleNotes"'},
    )


# ---------- Helpers ----------


class NoteIn(BaseModel):
    title: str
    content: str = ""


def clean_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise HTTPException(400, "Title cannot be empty.")
    if len(title) > 100:
        raise HTTPException(400, "Title is too long (max 100 characters).")
    if INVALID_TITLE_CHARS.search(title) or title.startswith("."):
        raise HTTPException(
            400, 'Title cannot start with "." or contain < > : " / \\ | ? *'
        )
    return title


def note_path(title: str) -> Path:
    path = (NOTES_DIR / f"{clean_title(title)}.md").resolve()
    if path.parent != NOTES_DIR:
        raise HTTPException(400, "Invalid title.")
    return path


def get_tags(content: str) -> list[str]:
    return sorted({tag.lower() for tag in TAG_PATTERN.findall(content)})


def note_info(path: Path, content: str | None = None) -> dict:
    if content is None:
        content = path.read_text(encoding="utf-8")
    modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return {
        "title": path.stem,
        "modified": modified.isoformat(),
        "tags": get_tags(content),
        "snippet": content[:150],
    }


def all_notes() -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in NOTES_DIR.glob("*.md")
    ]


# ---------- API ----------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/notes")
def list_notes(q: str = "", tag: str = ""):
    """List notes, newest first. `q` searches title + content,
    `tag` filters by tag (without the #)."""
    words = q.lower().split()
    results = []
    for path, content in all_notes():
        text = f"{path.stem}\n{content}".lower()
        if words and not all(word in text for word in words):
            continue
        info = note_info(path, content)
        if tag and tag.lower().lstrip("#") not in info["tags"]:
            continue
        results.append(info)
    results.sort(key=lambda note: note["modified"], reverse=True)
    return results


@app.get("/api/tags")
def list_tags():
    counts: dict[str, int] = {}
    for _, content in all_notes():
        for tag in get_tags(content):
            counts[tag] = counts.get(tag, 0) + 1
    return [{"tag": t, "count": c} for t, c in sorted(counts.items())]


@app.get("/api/notes/{title}")
def get_note(title: str):
    path = note_path(title)
    if not path.exists():
        raise HTTPException(404, "Note not found.")
    content = path.read_text(encoding="utf-8")
    return {**note_info(path, content), "content": content}


@app.post("/api/notes", status_code=201)
def create_note(note: NoteIn):
    path = note_path(note.title)
    if path.exists():
        raise HTTPException(409, "A note with this title already exists.")
    path.write_text(note.content, encoding="utf-8")
    return {**note_info(path, note.content), "content": note.content}


@app.put("/api/notes/{title}")
def update_note(title: str, note: NoteIn):
    old_path = note_path(title)
    if not old_path.exists():
        raise HTTPException(404, "Note not found.")
    new_path = note_path(note.title)
    if new_path != old_path:
        if new_path.exists():
            raise HTTPException(
                409, "A note with this title already exists."
            )
        old_path.rename(new_path)
    new_path.write_text(note.content, encoding="utf-8")
    return {**note_info(new_path, note.content), "content": note.content}


@app.delete("/api/notes/{title}", status_code=204)
def delete_note(title: str):
    path = note_path(title)
    if not path.exists():
        raise HTTPException(404, "Note not found.")
    path.unlink()


# ---------- Frontend ----------


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
