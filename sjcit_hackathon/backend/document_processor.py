"""Document ingestion, chunking, SHA-256 digest calculation, and version lifecycle."""
from __future__ import annotations
import io
import re
import uuid
from typing import Any
from crypto_utils import now_utc_iso, sha256_digest
from database import get_connection
from ledger_engine import AuditLedger

try:
    import pypdf
except ImportError:
    pypdf = None


def extract_text_from_bytes(content: bytes, filename: str) -> tuple[list[dict[str, Any]], str | None]:
    """
    Extract text chunks with location metadata (page, section, char_offset).
    Returns (chunks, error_message).
    """
    if not content or len(content.strip()) == 0:
        return [], "Uploaded file is empty (0 bytes)"

    chunks: list[dict[str, Any]] = []

    # PDF parsing
    if filename.lower().endswith(".pdf"):
        if not pypdf:
            return [], "pypdf parser is not available in the environment"
        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
            if len(reader.pages) == 0:
                return [], "PDF contains 0 pages"
            for page_idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                # Chunk page text by paragraphs / blocks
                paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page_text) if p.strip()]
                offset = 0
                for para in paragraphs:
                    # extract simple section heading if present
                    first_line = para.split("\n")[0][:60]
                    section = first_line if len(first_line) > 3 and not first_line.endswith(".") else f"Page {page_idx}"
                    chunks.append({
                        "page": page_idx,
                        "section": section,
                        "char_offset": offset,
                        "text": para,
                        "token_count": len(para.split()),
                    })
                    offset += len(para) + 2
            if not chunks:
                return [], "Could not extract readable text from PDF pages"
            return chunks, None
        except Exception as e:
            return [], f"Failed to parse PDF document: {str(e)}"

    # TXT / Markdown parsing
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as e:
            return [], f"Encoding error reading text file: {str(e)}"

    if not text.strip():
        return [], "Document contains no text"

    # Chunk by paragraphs or sections
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    current_page = 1
    offset = 0
    line_count = 0

    for block in blocks:
        # Approximate page numbering (every ~45 lines or ~2000 chars is page increment)
        line_count += block.count("\n") + 2
        if line_count > 40:
            current_page += 1
            line_count = 0

        # Detect markdown heading or first sentence as section
        section = "Section 1"
        match = re.match(r"^(#{1,4}\s+[^\n]+)", block)
        if match:
            section = match.group(1).lstrip("#").strip()
        else:
            first_line = block.split("\n")[0][:50]
            if len(first_line) > 3:
                section = first_line

        chunks.append({
            "page": current_page,
            "section": section,
            "char_offset": offset,
            "text": block,
            "token_count": len(block.split()),
        })
        offset += len(block) + 2

    return chunks, None


class DocumentService:
    @staticmethod
    def ingest_document(
        tenant_id: str,
        user_id: str,
        title: str,
        filename: str,
        content_bytes: bytes,
    ) -> dict[str, Any]:
        """Upload an initial document and version 1."""
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        now = now_utc_iso()
        digest = f"sha256:{sha256_digest(content_bytes)}"
        chunks, error = extract_text_from_bytes(content_bytes, filename)

        status = "failed" if error else "active"
        version_id = f"ver_{uuid.uuid4().hex[:12]}"
        version_num = 1

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, tenant_id, title, original_filename, media_type, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, tenant_id, title, filename, "application/pdf" if filename.endswith(".pdf") else "text/plain", user_id, now),
            )

            conn.execute(
                """
                INSERT INTO document_versions (id, doc_id, tenant_id, version_num, content_digest, status, failure_reason, created_by, created_at, activated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version_id, doc_id, tenant_id, version_num, digest, status, error, user_id, now, now if status == "active" else None),
            )

            if status == "active":
                for chunk in chunks:
                    chunk_id = f"chk_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """
                        INSERT INTO document_chunks (id, doc_id, version_num, tenant_id, page, section, char_offset, text, token_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (chunk_id, doc_id, version_num, tenant_id, chunk["page"], chunk["section"], chunk["char_offset"], chunk["text"], chunk["token_count"]),
                    )

        # Audit event
        AuditLedger.append_event(
            event_type="document_uploaded",
            actor_id=user_id,
            tenant_id=tenant_id,
            resource_id=doc_id,
            action="upload_document",
            decision="success" if status == "active" else "failure",
            details={
                "version_num": version_num,
                "content_digest": digest,
                "status": status,
                "chunks_count": len(chunks),
                "error": error,
            },
        )

        # Trigger vector index rebuild in memory (Layer 2)
        if status == "active":
            try:
                from vector_store import InMemoryVectorDB
                InMemoryVectorDB.get_instance().rebuild_tenant(tenant_id)
            except Exception:
                pass

        return {
            "document_id": doc_id,
            "version_num": version_num,
            "title": title,
            "filename": filename,
            "content_digest": digest,
            "status": status,
            "chunks_count": len(chunks),
            "error": error,
        }

    @staticmethod
    def replace_version(
        doc_id: str,
        tenant_id: str,
        user_id: str,
        content_bytes: bytes,
        filename: str,
    ) -> dict[str, Any]:
        """Atomic version replacement: supersedes previous version and activates new version."""
        now = now_utc_iso()
        digest = f"sha256:{sha256_digest(content_bytes)}"
        chunks, error = extract_text_from_bytes(content_bytes, filename)
        status = "failed" if error else "active"

        with get_connection() as conn:
            # Check document existence and ownership
            doc = conn.execute("SELECT * FROM documents WHERE id = ? AND tenant_id = ?", (doc_id, tenant_id)).fetchone()
            if not doc:
                raise ValueError("Document not found or does not belong to authorized tenant")

            # Determine next version number
            last_ver = conn.execute(
                "SELECT MAX(version_num) as max_v FROM document_versions WHERE doc_id = ?", (doc_id,)
            ).fetchone()
            next_version_num = (last_ver["max_v"] + 1) if last_ver and last_ver["max_v"] else 2

            version_id = f"ver_{uuid.uuid4().hex[:12]}"

            if status == "active":
                # Atomically supersede any current active versions for this document
                conn.execute(
                    "UPDATE document_versions SET status = 'superseded' WHERE doc_id = ? AND status = 'active'",
                    (doc_id,),
                )

            # Insert new version
            conn.execute(
                """
                INSERT INTO document_versions (id, doc_id, tenant_id, version_num, content_digest, status, failure_reason, created_by, created_at, activated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version_id, doc_id, tenant_id, next_version_num, digest, status, error, user_id, now, now if status == "active" else None),
            )

            # Insert chunks if active
            if status == "active":
                for chunk in chunks:
                    chunk_id = f"chk_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """
                        INSERT INTO document_chunks (id, doc_id, version_num, tenant_id, page, section, char_offset, text, token_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (chunk_id, doc_id, next_version_num, tenant_id, chunk["page"], chunk["section"], chunk["char_offset"], chunk["text"], chunk["token_count"]),
                    )

        # Audit events for version replacement
        AuditLedger.append_event(
            event_type="document_version_activated",
            actor_id=user_id,
            tenant_id=tenant_id,
            resource_id=doc_id,
            action="replace_version",
            decision="success" if status == "active" else "failure",
            details={
                "version_num": next_version_num,
                "superseded_previous": next_version_num - 1,
                "content_digest": digest,
                "status": status,
                "error": error,
            },
        )

        # Trigger vector index rebuild in memory (Layer 2)
        if status == "active":
            try:
                from vector_store import InMemoryVectorDB
                InMemoryVectorDB.get_instance().rebuild_tenant(tenant_id)
            except Exception:
                pass

        return {
            "document_id": doc_id,
            "version_num": next_version_num,
            "content_digest": digest,
            "status": status,
            "chunks_count": len(chunks),
            "error": error,
        }

    @staticmethod
    def list_documents(tenant_id: str) -> list[dict[str, Any]]:
        """List all documents belonging to tenant with version history and SHA-256 digests."""
        with get_connection() as conn:
            docs = conn.execute(
                "SELECT * FROM documents WHERE tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()

            result = []
            for doc in docs:
                versions = conn.execute(
                    "SELECT id, version_num, content_digest, status, failure_reason, created_at, activated_at FROM document_versions WHERE doc_id = ? ORDER BY version_num DESC",
                    (doc["id"],),
                ).fetchall()
                active_ver = next((v for v in versions if v["status"] == "active"), None)
                result.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "original_filename": doc["original_filename"],
                    "created_at": doc["created_at"],
                    "current_version": active_ver["version_num"] if active_ver else None,
                    "current_digest": active_ver["content_digest"] if active_ver else None,
                    "versions": [dict(v) for v in versions],
                })
        return result
