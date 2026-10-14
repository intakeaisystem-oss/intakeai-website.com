"""Persistent marketing knowledge store (SQLite, stdlib).

Guarantees
- Every record is schema-validated before it is written.
- Exact duplicates (same kind + same content) are detected and not re-inserted.
- A record with the same natural key but different content is a *conflict*:
  by default it raises; with on_conflict="version" the old content is preserved
  in record_history and the record gets a new version; with "skip" nothing changes.
  Nothing is ever silently overwritten.
- Nothing is hard-deleted; use archive().
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .schemas import CONFIDENCE, RECORD, validate

PREFIX = {
    "customer_insight": "INS", "voc_finding": "VOC", "offer": "OFR", "copy_asset": "CPY",
    "ad_concept": "ADC", "ad_variant": "ADV", "campaign_hypothesis": "HYP", "objection": "OBJ",
    "funnel_audit": "FUN", "experiment": "EXP", "campaign_result": "RES", "approach": "APR",
    "source": "SRC", "customer_profile": "PRF",
}

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    product TEXT,
    audience TEXT,
    confidence TEXT,
    basis TEXT,
    status TEXT DEFAULT 'active',
    tags TEXT DEFAULT '[]',
    sources TEXT DEFAULT '[]',
    data TEXT NOT NULL,
    natural_key TEXT,
    content_hash TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_kind_nkey ON records(kind, natural_key) WHERE natural_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_kind_hash ON records(kind, content_hash);
CREATE INDEX IF NOT EXISTS ix_product ON records(product);
CREATE TABLE IF NOT EXISTS record_history (
    hid INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    snapshot TEXT NOT NULL,
    change_note TEXT,
    changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


class ConflictError(Exception):
    def __init__(self, existing_id: str, message: str):
        super().__init__(message)
        self.existing_id = existing_id


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash(record: dict) -> str:
    core = {k: record.get(k) for k in ("kind", "title", "product", "audience", "data")}
    if isinstance(core.get("title"), str):
        core["title"] = " ".join(core["title"].lower().split())
    return hashlib.sha1(_canon(core).encode()).hexdigest()


class KnowledgeStore:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA_SQL)
        self.conn.execute("INSERT OR IGNORE INTO meta VALUES ('schema_version','1')")
        self.conn.commit()

    # ------------------------------------------------------------- writes
    def add(self, record: dict, on_conflict: str = "error", note: str = "") -> tuple[str, str]:
        """Insert a record. Returns (id, action) where action is one of
        created | duplicate | versioned | skipped. Raises ConflictError when the
        natural key exists with different content and on_conflict == 'error'."""
        if on_conflict not in ("error", "skip", "version"):
            raise ValueError("on_conflict must be error|skip|version")
        record = {k: v for k, v in record.items() if v is not None}
        validate(record, RECORD)
        h = content_hash(record)
        kind = record["kind"]

        dup = self.conn.execute(
            "SELECT id FROM records WHERE kind=? AND content_hash=?", (kind, h)).fetchone()
        if dup:
            return dup["id"], "duplicate"

        nkey = record.get("natural_key")
        if nkey:
            existing = self.conn.execute(
                "SELECT * FROM records WHERE kind=? AND natural_key=?", (kind, nkey)).fetchone()
            if existing:
                if on_conflict == "error":
                    raise ConflictError(existing["id"], (
                        f"{kind} with natural_key {nkey!r} already exists as {existing['id']} "
                        "with different content; use on_conflict='version' to keep both versions "
                        "or 'skip' to keep the existing one"))
                if on_conflict == "skip":
                    return existing["id"], "skipped"
                self._update_row(existing["id"], record, h, note or "new version on import")
                return existing["id"], "versioned"

        rid = record.get("id") or f"{PREFIX[kind]}-{h[:10]}"
        if self.conn.execute("SELECT 1 FROM records WHERE id=?", (rid,)).fetchone():
            if on_conflict == "error":
                raise ConflictError(rid, f"id {rid} already exists with different content")
            if on_conflict == "skip":
                return rid, "skipped"
            self._update_row(rid, record, h, note or "new version (same id)")
            return rid, "versioned"
        now = _now()
        self.conn.execute(
            "INSERT INTO records (id,kind,title,product,audience,confidence,basis,status,tags,sources,"
            "data,natural_key,content_hash,version,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
            (rid, kind, record["title"], record.get("product"), record.get("audience"),
             record.get("confidence"), record.get("basis"), record.get("status", "active"),
             _canon(record.get("tags", [])), _canon(record.get("sources", [])), _canon(record["data"]),
             nkey, h, now, now))
        self.conn.commit()
        return rid, "created"

    def preview(self, record: dict, on_conflict: str = "error") -> tuple[str, str | None]:
        """What add() would do, without writing: (action, existing_id).
        action: created | duplicate | versioned | skipped | conflict."""
        record = {k: v for k, v in record.items() if v is not None}
        validate(record, RECORD)
        kind, h = record["kind"], content_hash(record)
        dup = self.conn.execute("SELECT id FROM records WHERE kind=? AND content_hash=?", (kind, h)).fetchone()
        if dup:
            return "duplicate", dup["id"]
        nkey = record.get("natural_key")
        ex = self.conn.execute("SELECT id FROM records WHERE kind=? AND natural_key=?", (kind, nkey)).fetchone() if nkey else None
        if not ex and record.get("id"):
            ex = self.conn.execute("SELECT id FROM records WHERE id=?", (record["id"],)).fetchone()
        if ex:
            return {"error": "conflict", "skip": "skipped", "version": "versioned"}[on_conflict], ex["id"]
        return "created", None

    def update(self, rid: str, changes: dict, note: str = "") -> dict:
        """Apply changes (top-level fields or a partial 'data' dict merged in).
        The previous version is kept in history."""
        cur = self.get(rid)
        if cur is None:
            raise KeyError(rid)
        new = {k: cur[k] for k in ("kind", "title", "product", "audience", "confidence", "basis",
                                   "tags", "sources", "status", "data", "natural_key") if cur.get(k) is not None}
        for k, v in changes.items():
            if k == "data":
                new["data"] = {**new["data"], **v}
            else:
                new[k] = v
        new = {k: v for k, v in new.items() if v is not None}
        validate(new, RECORD)
        h = content_hash(new)
        unchanged = h == cur["content_hash"] and all(new.get(k) == cur.get(k) for k in ("confidence", "basis", "tags", "sources", "status"))
        if unchanged:
            return cur  # no-op: nothing changed, no history entry
        self._update_row(rid, new, h, note or "update")
        return self.get(rid)

    def _update_row(self, rid: str, record: dict, h: str, note: str) -> None:
        old = self.conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
        snapshot = self._row_to_dict(old)
        self.conn.execute(
            "INSERT INTO record_history (record_id,version,snapshot,change_note,changed_at) VALUES (?,?,?,?,?)",
            (rid, old["version"], _canon(snapshot), note, _now()))
        self.conn.execute(
            "UPDATE records SET title=?,product=?,audience=?,confidence=?,basis=?,status=?,tags=?,sources=?,"
            "data=?,content_hash=?,version=version+1,updated_at=? WHERE id=?",
            (record["title"], record.get("product"), record.get("audience"), record.get("confidence"),
             record.get("basis"), record.get("status", old["status"]), _canon(record.get("tags", [])),
             _canon(record.get("sources", [])), _canon(record["data"]), h, _now(), rid))
        self.conn.commit()

    def archive(self, rid: str, reason: str) -> dict:
        return self.update(rid, {"status": "archived"}, note=f"archived: {reason}")

    # ------------------------------------------------------------- reads
    @staticmethod
    def _row_to_dict(row) -> dict:
        d = dict(row)
        for k in ("tags", "sources", "data"):
            d[k] = json.loads(d[k]) if d.get(k) else ([] if k != "data" else {})
        return d

    def get(self, rid: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
        return self._row_to_dict(row) if row else None

    def history(self, rid: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM record_history WHERE record_id=? ORDER BY version", (rid,)).fetchall()
        return [{"version": r["version"], "changed_at": r["changed_at"], "note": r["change_note"],
                 "snapshot": json.loads(r["snapshot"])} for r in rows]

    def find(self, kind: str | list | None = None, product: str | None = None, audience: str | None = None,
             tag: str | None = None, text: str | None = None, min_confidence: str | None = None,
             include_archived: bool = False, limit: int = 500) -> list[dict]:
        sql, args = "SELECT * FROM records WHERE 1=1", []
        if kind:
            kinds = [kind] if isinstance(kind, str) else list(kind)
            sql += f" AND kind IN ({','.join('?' * len(kinds))})"
            args += kinds
        if product:
            sql += " AND (product = ? OR product IS NULL)"
            args.append(product)
        if audience:
            sql += " AND (audience LIKE ? OR audience IS NULL)"
            args.append(f"%{audience}%")
        if tag:
            sql += " AND tags LIKE ?"
            args.append(f'%"{tag}"%')
        if text:
            sql += " AND (title LIKE ? OR data LIKE ?)"
            args += [f"%{text}%", f"%{text}%"]
        if not include_archived:
            sql += " AND status != 'archived'"
        sql += " ORDER BY updated_at DESC LIMIT ?"
        args.append(limit)
        rows = [self._row_to_dict(r) for r in self.conn.execute(sql, args).fetchall()]
        if min_confidence:
            floor = CONFIDENCE.index(min_confidence)
            rows = [r for r in rows if r.get("confidence") in CONFIDENCE and CONFIDENCE.index(r["confidence"]) >= floor]
        return rows

    def stats(self) -> dict:
        rows = self.conn.execute(
            "SELECT kind, COUNT(*) n FROM records WHERE status!='archived' GROUP BY kind").fetchall()
        hist = self.conn.execute("SELECT COUNT(*) FROM record_history").fetchone()[0]
        return {"by_kind": {r["kind"]: r["n"] for r in rows}, "total": sum(r["n"] for r in rows),
                "history_entries": hist, "path": self.path}

    def close(self):
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
