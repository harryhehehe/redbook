"""SQLite 存档：帖子 + 引流 PDF 历史记录。

数据库文件：项目根目录 archive.db
- 本地 EXE：永久保留
- Streamlit Cloud：实例运行期间保留；重新部署（git push）会重置

表结构：
  posts(id, created_at, topic, audience, mode, template_id,
        extra_notes, body_text, blocks_json)
  pdfs(id, created_at, keyword, resource_name, audience,
       extra_instructions, content_json, pdf_blob)
"""
from __future__ import annotations
import io
import json
import sqlite3
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "archive.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    topic       TEXT NOT NULL,
    audience    TEXT,
    mode        TEXT,            -- 'template' | 'free'
    template_id TEXT,
    extra_notes TEXT,
    body_text   TEXT NOT NULL,
    blocks_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pdfs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at         TEXT NOT NULL,
    keyword            TEXT NOT NULL,
    resource_name      TEXT NOT NULL,
    audience           TEXT,
    extra_instructions TEXT,
    content_json       TEXT NOT NULL,
    pdf_blob           BLOB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdfs_created  ON pdfs(created_at DESC);
"""


@contextmanager
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(_SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- Posts ----------
def save_post(topic: str, audience: str, mode: str, template_id: str | None,
              extra_notes: str | None, body_text: str, blocks: list[dict]) -> int:
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO posts
               (created_at, topic, audience, mode, template_id,
                extra_notes, body_text, blocks_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (_now(), topic, audience, mode, template_id,
             extra_notes or "", body_text,
             json.dumps(blocks, ensure_ascii=False)),
        )
        return cur.lastrowid


def list_posts(keyword: str = "", limit: int = 200) -> list[sqlite3.Row]:
    sql = "SELECT id, created_at, topic, audience, mode, template_id FROM posts"
    args: tuple = ()
    if keyword:
        sql += " WHERE topic LIKE ? OR body_text LIKE ?"
        args = (f"%{keyword}%", f"%{keyword}%")
    sql += " ORDER BY created_at DESC LIMIT ?"
    args = args + (limit,)
    with _conn() as c:
        return list(c.execute(sql, args))


def get_post(post_id: int) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()


def delete_post(post_id: int):
    with _conn() as c:
        c.execute("DELETE FROM posts WHERE id=?", (post_id,))


# ---------- PDFs ----------
def save_pdf(keyword: str, resource_name: str, audience: str,
             extra_instructions: str, content: dict, pdf_bytes: bytes) -> int:
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO pdfs
               (created_at, keyword, resource_name, audience,
                extra_instructions, content_json, pdf_blob)
               VALUES (?,?,?,?,?,?,?)""",
            (_now(), keyword, resource_name, audience or "",
             extra_instructions or "",
             json.dumps(content, ensure_ascii=False), pdf_bytes),
        )
        return cur.lastrowid


def list_pdfs(keyword: str = "", limit: int = 200) -> list[sqlite3.Row]:
    sql = "SELECT id, created_at, keyword, resource_name, audience, LENGTH(pdf_blob) as size FROM pdfs"
    args: tuple = ()
    if keyword:
        sql += " WHERE keyword LIKE ? OR resource_name LIKE ?"
        args = (f"%{keyword}%", f"%{keyword}%")
    sql += " ORDER BY created_at DESC LIMIT ?"
    args = args + (limit,)
    with _conn() as c:
        return list(c.execute(sql, args))


def get_pdf(pdf_id: int) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM pdfs WHERE id=?", (pdf_id,)).fetchone()


def delete_pdf(pdf_id: int):
    with _conn() as c:
        c.execute("DELETE FROM pdfs WHERE id=?", (pdf_id,))


# ---------- 统计 + 导出 ----------
def stats() -> dict:
    with _conn() as c:
        np = c.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        npdf = c.execute("SELECT COUNT(*) FROM pdfs").fetchone()[0]
        size_pdf = c.execute("SELECT COALESCE(SUM(LENGTH(pdf_blob)),0) FROM pdfs").fetchone()[0]
        return {"posts": np, "pdfs": npdf, "pdf_total_bytes": size_pdf}


def export_zip() -> bytes:
    """全部历史导出成 zip：帖子用 .txt、PDF 用 .pdf、JSON 元数据另附。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        with _conn() as c:
            for r in c.execute("SELECT * FROM posts"):
                stem = f"posts/{r['id']:04d}_{_safe(r['topic'])}"
                z.writestr(stem + ".txt", r["body_text"])
                z.writestr(stem + ".json", json.dumps(dict(r), ensure_ascii=False, indent=2))
            for r in c.execute("SELECT * FROM pdfs"):
                stem = f"pdfs/{r['id']:04d}_{_safe(r['resource_name'])}"
                z.writestr(stem + ".pdf", r["pdf_blob"])
                meta = {k: r[k] for k in r.keys() if k != "pdf_blob"}
                z.writestr(stem + ".json", json.dumps(meta, ensure_ascii=False, indent=2))
    return buf.getvalue()


def _safe(s: str) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    out = "".join("_" if c in bad else c for c in (s or "untitled"))
    return out[:60].strip()
