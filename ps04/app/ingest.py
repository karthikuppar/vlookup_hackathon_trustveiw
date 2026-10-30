"""Document ingestion: validate -> store -> hash -> extract -> chunk -> index -> atomically activate."""
from __future__ import annotations
import hashlib, io, re, uuid
from pathlib import Path

from .audit import now
from .db import tx

CHUNK_BUDGET = 800
HEADING = re.compile(r"^(#{1,6}\s+.+|\d+(\.\d+)*[.)]?\s+[A-Z].{0,78}|[A-Z][A-Z0-9 ,&/\-]{3,78})$")


class IngestRejected(ValueError):
    """Upload refused before any version record is created."""


def validate(filename: str, data: bytes, settings) -> str:
    name = Path(filename or "").name
    ext = Path(name).suffix.lower()
    if not name or ext not in settings.allowed_media:
        raise IngestRejected(f"Unsupported file type; allowed: {', '.join(settings.allowed_media)}")
    if not data:
        raise IngestRejected("File is empty")
    if len(data) > settings.max_upload_bytes:
        raise IngestRejected(f"File exceeds the {settings.max_upload_bytes} byte limit")
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise IngestRejected("File content does not match the .pdf type")
    return ext


def extract(data: bytes, ext: str) -> list[tuple[int | None, str]]:
    """Local text extraction. Returns [(page_or_None, text)]; raises ValueError with an actionable message."""
    if ext in (".txt", ".md"):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("Text file is not valid UTF-8; re-save it as UTF-8 and upload again")
        pages = [(None, text)]
    else:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError("PDF is encrypted; upload an unprotected copy")
            pages = [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
        except ValueError:
            raise
        except Exception as e:  # corrupt or unsupported structure
            raise ValueError(f"PDF could not be parsed ({type(e).__name__}); the file may be corrupt")
    if not any(t.strip() for _, t in pages):
        raise ValueError("No extractable text found (scanned or image-only document?); run OCR first")
    return pages


def chunk(pages) -> list[dict]:
    """Paragraph-based chunks that keep page, section heading and character offsets into the extracted text."""
    out, offset, section = [], 0, None
    for page, text in pages:
        buf, buf_start, buf_section = [], None, None

        def flush():
            nonlocal buf, buf_start
            if buf:
                body = "\n\n".join(t for t, _ in buf)
                out.append({"page": page, "section": buf_section, "char_start": buf_start, "char_end": buf_start + len(body), "text": body})
            buf, buf_start = [], None

        for m in re.finditer(r"\S[\s\S]*?(?=\n[ \t]*\n|\Z)", text):
            para = m.group(0).strip()
            first = para.splitlines()[0].strip()
            if HEADING.match(first) and len(para.splitlines()) == 1:
                flush()
                section = first.lstrip("# ").strip()
                buf_section = section
                buf, buf_start = [(first, 0)], offset + m.start()
                continue
            if HEADING.match(first):  # heading directly followed by body text, no blank line between
                flush()
                section = buf_section = first.lstrip("# ").strip()
                buf, buf_start = [(para, 0)], offset + m.start()
                continue
            if buf_start is None:
                buf_start, buf_section = offset + m.start(), section
            if sum(len(t) for t, _ in buf) + len(para) > CHUNK_BUDGET and buf and not (len(buf) == 1 and HEADING.match(buf[0][0])):
                flush()
                buf_start, buf_section = offset + m.start(), section
            buf.append((para, 0))
        flush()
        offset += len(text) + 2
    # split any chunk that is still far over budget (very long paragraph) on sentence boundaries
    final = []
    for c in out:
        if len(c["text"]) <= CHUNK_BUDGET * 1.5:
            final.append(c)
            continue
        cur = ""
        for s in re.split(r"(?<=[.!?])\s+", c["text"]):
            if cur and len(cur) + len(s) > CHUNK_BUDGET:
                final.append({**c, "text": cur})
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur:
            final.append({**c, "text": cur})
    return [c for c in final if c["text"].strip()]


def ingest_version(conn, ledger, settings, *, tenant_id, user_id, filename, data, title=None, document_id=None) -> dict:
    """Create a new immutable version. Only becomes current if processing fully succeeds."""
    ext = validate(filename, data, settings)
    digest = hashlib.sha256(data).hexdigest()
    version_id = f"ver_{uuid.uuid4().hex}"
    store = Path(settings.data_dir) / "tenants" / tenant_id
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{version_id}{ext}"
    path.write_bytes(data)

    with tx(conn):
        if document_id is None:
            document_id = f"doc_{uuid.uuid4().hex}"
            conn.execute("INSERT INTO documents VALUES(?,?,?,?,?)", (document_id, tenant_id, (title or Path(filename).stem)[:200], user_id, now()))
        n = conn.execute("SELECT COALESCE(MAX(version_no),0)+1 FROM document_versions WHERE document_id=?", (document_id,)).fetchone()[0]
        conn.execute("INSERT INTO document_versions(id,document_id,tenant_id,version_no,filename,media_type,uploaded_by,uploaded_at,sha256,size,status,file_path)"
                     " VALUES(?,?,?,?,?,?,?,?,?,?,'processing',?)",
                     (version_id, document_id, tenant_id, n, Path(filename).name, ext.lstrip("."), user_id, now(), digest, len(data), str(path)))
        ledger.append(conn, "document.upload", actor=user_id, tenant_id=tenant_id, document_id=document_id, version_id=version_id, version_no=n, sha256=digest)

    try:
        chunks = chunk(extract(data, ext))
        if not chunks:
            raise ValueError("Document produced no indexable content")
    except ValueError as e:
        with tx(conn):
            conn.execute("UPDATE document_versions SET status='failed', error=? WHERE id=?", (str(e), version_id))
            ledger.append(conn, "document.ingest_failed", actor=user_id, tenant_id=tenant_id, document_id=document_id, version_id=version_id, error=str(e))
        return {"document_id": document_id, "version_id": version_id, "version_no": n, "status": "failed", "error": str(e)}

    with tx(conn):  # activation is atomic: index + supersede previous + mark current
        for i, c in enumerate(chunks):
            conn.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (f"chk_{uuid.uuid4().hex}", version_id, document_id, tenant_id, i, c["page"], c["section"], c["char_start"], c["char_end"], c["text"]))
        prev = conn.execute("SELECT id, version_no FROM document_versions WHERE document_id=? AND is_current=1", (document_id,)).fetchone()
        if prev:
            conn.execute("UPDATE document_versions SET is_current=0, superseded_at=?, superseded_by_version=? WHERE id=?", (now(), version_id, prev["id"]))
        conn.execute("UPDATE document_versions SET status='ready', is_current=1 WHERE id=?", (version_id,))
        ledger.append(conn, "document.activate", actor=user_id, tenant_id=tenant_id, document_id=document_id, version_id=version_id,
                      version_no=n, superseded_version=prev["id"] if prev else None, chunks=len(chunks))
    return {"document_id": document_id, "version_id": version_id, "version_no": n, "status": "ready", "chunks": len(chunks), "sha256": digest}
