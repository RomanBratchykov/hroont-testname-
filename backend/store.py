"""Small durable conversation store. Provider spending survives chat deletion."""

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

from backend.language import requires_translation


class Conflict(Exception):
    pass


class SessionCapacity(Exception):
    pass


class BudgetExceeded(Exception):
    pass


def micros(value: Decimal) -> int:
    return int((value * 1_000_000).to_integral_value(rounding=ROUND_CEILING))


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, updated_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id)
                    ON DELETE CASCADE, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
                    result TEXT, created_at REAL NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS active_conversation ON runs(conversation_id)
                    WHERE status IN ('queued', 'running');
                CREATE TABLE IF NOT EXISTS messages (
                    seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL, content TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS message_chat ON messages(conversation_id, seq);
                CREATE TABLE IF NOT EXISTS translations (
                    request_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE, english TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS guest_sessions (
                    id TEXT PRIMARY KEY, last_seen REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS conversation_owners (
                    conversation_id TEXT PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
                    owner TEXT NOT NULL REFERENCES guest_sessions(id));
                CREATE INDEX IF NOT EXISTS owner_chats ON conversation_owners(owner);
                CREATE TABLE IF NOT EXISTS spending (
                    id TEXT PRIMARY KEY, phase TEXT NOT NULL, reserved INTEGER NOT NULL,
                    spent INTEGER NOT NULL DEFAULT 0);
            """)
        self.expire()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover(self):
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET status='cancelled' WHERE status IN ('queued','running')"
            )

    def expire(self):
        with self.connect() as db:
            db.execute(
                "DELETE FROM conversations WHERE updated_at < ?",
                (time.time() - 30 * 86400,),
            )

    def admit_guest(self, identifier: str, limit: int | None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            now = time.time()
            # An in-flight model request keeps its slot even if its browser is idle.
            active = {
                row[0]
                for row in db.execute(
                    "SELECT id FROM guest_sessions WHERE last_seen > ? OR id IN ("
                    "SELECT o.owner FROM conversation_owners o JOIN runs r "
                    "ON r.conversation_id=o.conversation_id WHERE r.status IN ('queued','running'))",
                    (now - 1800,),
                )
            }
            if limit is not None and identifier not in active and len(active) >= limit:
                raise SessionCapacity(
                    "I’m helping four users right now. Please try again when a slot becomes available."
                )
            db.execute(
                "INSERT INTO guest_sessions VALUES (?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen",
                (identifier, now),
            )

    def owns(self, chat: str, owner: str) -> bool:
        with self.connect() as db:
            return (
                db.execute(
                    "SELECT 1 FROM conversation_owners WHERE conversation_id=? AND owner=?",
                    (chat, owner),
                ).fetchone()
                is not None
            )

    def begin(
        self,
        chat: str,
        request: str,
        content: str,
        mode: str,
        files: list,
        owner: str | None = None,
    ):
        fingerprint = hashlib.sha256(
            json.dumps([chat, content, mode, files], sort_keys=True).encode()
        ).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if (
                owner is not None
                and db.execute(
                    "SELECT 1 FROM conversations WHERE id=?", (chat,)
                ).fetchone()
                and not db.execute(
                    "SELECT 1 FROM conversation_owners WHERE conversation_id=? AND owner=?",
                    (chat, owner),
                ).fetchone()
            ):
                raise PermissionError("Chat not found.")
            existing = db.execute(
                "SELECT * FROM runs WHERE id=?", (request,)
            ).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise Conflict("Request ID was already used for different input.")
                return dict(existing)
            if db.execute(
                "SELECT 1 FROM runs WHERE conversation_id=? AND status IN ('queued','running')",
                (chat,),
            ).fetchone():
                raise Conflict(
                    "This chat already has an active turn. Stop it before submitting another."
                )
            now = time.time()
            db.execute(
                "INSERT INTO conversations VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at",
                (chat, content[:60] or "File analysis", now),
            )
            if owner is not None:
                db.execute(
                    "INSERT OR IGNORE INTO conversation_owners VALUES (?,?)",
                    (chat, owner),
                )
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,NULL,?)",
                (request, chat, fingerprint, "queued", now),
            )
            db.execute(
                "INSERT INTO messages(id,conversation_id,role,content,created_at) VALUES (?,?,?,?,?)",
                (request, chat, "user", content, now),
            )
        return None

    def run_record(self, request):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (request,)).fetchone()
            return dict(row) if row else None

    def running(self, request):
        with self.connect() as db:
            row = db.execute(
                "UPDATE runs SET status='running' WHERE id=? AND status='queued'",
                (request,),
            )
            if not row.rowcount:
                raise Conflict("Turn was cancelled or deleted.")

    def finish(self, request: str, event: dict, status: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (request,)).fetchone()
            if not row or row["status"] not in {"queued", "running"}:
                return
            db.execute(
                "UPDATE runs SET status=?, result=? WHERE id=?",
                (status, json.dumps(event), request),
            )
            if event.get("type") == "answer":
                now = time.time()
                db.execute(
                    "INSERT INTO messages(id,conversation_id,role,content,created_at) VALUES (?,?,?,?,?)",
                    (
                        request + ":answer",
                        row["conversation_id"],
                        "assistant",
                        event["content"],
                        now,
                    ),
                )
                db.execute(
                    "UPDATE conversations SET updated_at=? WHERE id=?",
                    (now, row["conversation_id"]),
                )

    def history(self, chat, limit=30, before=None, for_model=False):
        with self.connect() as db:
            rows = db.execute(
                "SELECT m.*, t.english FROM messages m LEFT JOIN translations t ON t.request_id=m.id "
                "WHERE m.conversation_id=? AND m.seq < ? ORDER BY m.seq DESC LIMIT ?",
                (chat, before if before is not None else 9223372036854775807, limit),
            ).fetchall()
            result = []
            for row in reversed(rows):
                message = dict(row)
                english = message.pop("english")
                if for_model:
                    message["content"] = english or message["content"]
                    if requires_translation(message["content"]):
                        message["content"] = (
                            "[Non-English original retained locally; English translation unavailable.]"
                        )
                result.append(message)
            return result

    def list_chats(self, owner: str | None = None):
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM conversations WHERE ? IS NULL OR id IN "
                    "(SELECT conversation_id FROM conversation_owners WHERE owner=?) "
                    "ORDER BY updated_at DESC LIMIT 200",
                    (owner, owner),
                )
            ]

    def read(self, chat):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM conversations WHERE id=?", (chat,)
            ).fetchone()
        if row is None:
            return None
        return {**dict(row), "messages": self.history(chat, limit=500)}

    def delete(self, chat=None, owner: str | None = None):
        with self.connect() as db:
            if chat is None:
                db.execute(
                    "DELETE FROM conversations WHERE ? IS NULL OR id IN (SELECT conversation_id FROM conversation_owners WHERE owner=?)",
                    (owner, owner),
                )
            else:
                db.execute("DELETE FROM conversations WHERE id=?", (chat,))

    def rename(self, chat, title):
        with self.connect() as db:
            return bool(
                db.execute(
                    "UPDATE conversations SET title=? WHERE id=?", (title, chat)
                ).rowcount
            )

    def reserve(self, identifier: str, amount: Decimal, phase: str, limit: Decimal):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            used = db.execute(
                "SELECT COALESCE(SUM(reserved+spent),0) FROM spending WHERE phase=?",
                (phase,),
            ).fetchone()[0]
            total = db.execute(
                "SELECT COALESCE(SUM(reserved+spent),0) FROM spending"
            ).fetchone()[0]
            if (
                used + micros(amount) > micros(limit)
                or total + micros(amount) > 5_000_000
            ):
                raise BudgetExceeded()
            db.execute(
                "INSERT INTO spending(id,phase,reserved) VALUES (?,?,?)",
                (identifier, phase, micros(amount)),
            )

    def settle(self, identifier: str, actual: Decimal):
        with self.connect() as db:
            db.execute(
                "UPDATE spending SET reserved=0, spent=? WHERE id=?",
                (micros(actual), identifier),
            )

    def budget(self, phase):
        with self.connect() as db:
            row = db.execute(
                "SELECT COALESCE(SUM(spent),0), COALESCE(SUM(reserved),0) FROM spending WHERE phase=?",
                (phase,),
            ).fetchone()
        return {"spent_usd": row[0] / 1_000_000, "reserved_usd": row[1] / 1_000_000}
