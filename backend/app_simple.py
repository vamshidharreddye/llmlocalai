"""
Local AI backend with:
- Simple file indexing (file names + metadata)
- Vector DB (Chroma) with Ollama embeddings for content search
- Keyword-based file search on names/folders
- PDF summarization when user sends /filename.pdf
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import requests

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None

# -------------------------------------------------------------------
# Logging / env
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Folder to index. Override in .env with FILE_SEARCH_ROOT=
FILE_SEARCH_ROOT = os.getenv("FILE_SEARCH_ROOT", os.path.expanduser("~"))

# Models
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")  # CPU-friendly default
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# In-memory index (for name/folder search)
FILE_INDEX: List[Dict[str, Any]] = []

# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(
    title="Local AI Chatbot",
    description="File-aware local assistant using Ollama + Chroma",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------
class AskRequest(BaseModel):
    query: str
    model: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    sources: List[dict]
    error: Optional[str] = None
    markdown: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    dirs: Optional[List[str]] = None


class FileRequest(BaseModel):
    path: str
    model: Optional[str] = None


# -------------------------------------------------------------------
# Chroma client / collection
# -------------------------------------------------------------------
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_store")
os.makedirs(CHROMA_DIR, exist_ok=True)

# Guard Chromadb: some chromadb builds try to call telemetry functions and
# cause exceptions on import or at runtime. If chromadb can't be imported
# or constructed cleanly, disable vector features gracefully.
chroma_client = None
collection = None
if chromadb and Settings:
    try:
        chroma_client = chromadb.Client(
            Settings(
                persist_directory=CHROMA_DIR,
                anonymized_telemetry=False,
            )
        )
        collection = chroma_client.get_or_create_collection("local_docs")
    except Exception as e:
        logger.warning(f"Chroma disabled due to error: {e}")
        chroma_client = None
        collection = None

# -------------------------------------------------------------------
# Helpers: file metadata + extract text
# -------------------------------------------------------------------
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
PDF_EXTS = {".pdf"}

EXCLUDED_DIR_NAMES = {
    "AppData",
    "node_modules",
    ".git",
    "__pycache__",
    ".cache",
    ".vscode",
}

ALLOWED_EXTS = set()


def _file_kind(ext: str) -> str:
    ext = ext.lower()
    if ext in PDF_EXTS:
        return "pdf"
    if ext in IMAGE_EXTS:
        return "image"
    return "other"


def _ts_to_iso(ts: float) -> str:
    """
    Convert a timestamp to ISO string, but be robust to weird values
    (some system files on Windows can have invalid timestamps).
    """
    try:
        return datetime.fromtimestamp(ts).isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        # Fallback when OS returns an invalid timestamp
        logger.warning(f"Invalid timestamp encountered: {ts!r}")
        return "unknown"


def build_file_index(root: str) -> List[Dict[str, Any]]:
    """Walk filesystem under `root` and build index with metadata."""
    logger.info(f"Building file index under: {root}")
    index: List[Dict[str, Any]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip heavy/junk folders
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]

        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ALLOWED_EXTS and ext not in ALLOWED_EXTS:
                continue  # ignore images, binaries, etc. for now

            full_path = os.path.join(dirpath, name)
            try:
                stat = os.stat(full_path)
            except OSError:
                continue  # permission / transient errors

            kind = _file_kind(ext)

            entry = {
                "path": full_path,
                "name": name.lower(),
                "basename": name,
                "directory": dirpath,
                "extension": ext,
                "kind": kind,
                "created": _ts_to_iso(stat.st_ctime),
                "modified": _ts_to_iso(stat.st_mtime),
                "size_bytes": stat.st_size,
            }
            index.append(entry)

    logger.info(f"Indexed {len(index)} files (metadata)")
    return index


def extract_text_from_file(path: str, ext: str) -> str:
    """Extract plain text from supported file types."""
    ext = ext.lower()
    try:
        if ext in {".txt", ".md", ".rtf"}:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        if ext in PDF_EXTS:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                logger.warning("PyPDF2 not installed; skipping PDF text extraction")
                return ""
            text = ""
            with open(path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages[:20]:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
                    if len(text) > 20000:  # cap to keep prompt reasonable
                        break
            return text

        if ext == ".docx":
            try:
                import docx
            except ImportError:
                logger.warning("python-docx not installed; skipping .docx text")
                return ""
            doc = docx.Document(path)
            return "\n".join(p.text for p in doc.paragraphs)

        # .doc (old) is tricky; skip for now
        return ""

    except Exception as e:
        logger.error(f"extract_text_from_file error for {path}: {e}")
        return ""


def split_into_chunks(text: str, chunk_size: int = 800, overlap: int = 200) -> List[str]:
    """Split long text into overlapping chunks."""
    if not text:
        return []
    text = text.strip()
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = max(end - overlap, 0)
    return chunks


# -------------------------------------------------------------------
# Helpers: embeddings + vector search
# -------------------------------------------------------------------
def embed_text(texts: List[str]) -> List[List[float]]:
    """
    Call Ollama's /api/embeddings endpoint for a batch of texts.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    embeddings: List[List[float]] = []

    for t in texts:
        resp = requests.post(
            f"{base_url}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": t},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings.append(data["embedding"])
    return embeddings


def is_ollama_error(response_text: str) -> bool:
    if not response_text:
        return True
    s = response_text.lower()
    # common markers of error messages from call_ollama
    if s.startswith('❌'):
        return True
    if 'couldn\'t reach ollama' in s or 'failed while processing' in s or 'runner process has terminated' in s:
        return True
    return False


def vector_search(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    """Search the Chroma collection using query embeddings."""
    # If chroma is not available, skip vector search
    if not chroma_client or not collection:
        logger.debug("vector_search: chroma client not available, skipping")
        return []

    try:
        q_emb = embed_text([query])[0]
    except Exception as e:
        logger.error(f"vector_search embedding error: {e}")
        return []

    try:
        result = collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
        )
    except Exception as e:
        logger.error(f"Chroma query error: {e}")
        return []

    hits: List[Dict[str, Any]] = []
    if not result or not result.get("metadatas"):
        return hits

    metadatas = result["metadatas"][0]
    documents = result["documents"][0]

    # Group by file path to avoid tons of duplicate chunks
    seen_paths = set()
    for md, doc in zip(metadatas, documents):
        path = md.get("path")
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)

        hits.append(
            {
                "path": path,
                "name": md.get("filename"),
                "directory": md.get("directory"),
                "created": md.get("created"),
                "modified": md.get("modified"),
                "size_bytes": md.get("size_bytes"),
                "snippet": (doc or "")[:300],
                "type": _file_kind(os.path.splitext(path)[1]),
                "reason": "vector",
            }
        )

    return hits


# -------------------------------------------------------------------
# Helpers: name/folder search
# -------------------------------------------------------------------
def find_matching_files(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """
    Return files whose name or parent folder name roughly matches the query.

    Adds a `reason_detail` field showing the matching token or folder name to help
    explain why a file was returned.
    """
    if not FILE_INDEX:
        return []

    import re

    q = query.lower()
    raw_tokens = [t for t in re.split(r"\W+", q) if t]

    keywords: List[str] = []
    for t in raw_tokens:
        if len(t) < 3:
            continue  # skip tiny words
        keywords.append(t)
        if t.endswith("s") and len(t) > 3:
            keywords.append(t[:-1])  # resumes -> resume

    keywords = list(dict.fromkeys(keywords))
    if not keywords:
        return []

    hits: List[Dict[str, Any]] = []
    for entry in FILE_INDEX:
        name_lower = entry['name']
        folder_lower = os.path.basename(entry['directory']).lower()
        haystack = f"{name_lower} {folder_lower}"
        matched = False
        reason = None
        reason_detail = None
        for kw in keywords:
            if kw in name_lower:
                matched = True
                reason = 'name'
                reason_detail = f"matched '{kw}' in filename"
                break
            if kw in folder_lower:
                matched = True
                reason = 'folder'
                reason_detail = f"matched '{kw}' in folder name"
                break

        if matched:
            e = dict(entry)
            e['reason'] = reason or 'match'
            e['reason_detail'] = reason_detail or ''
            hits.append(e)
            if len(hits) >= max_results:
                break

    logger.info(f"find_matching_files: query='{query}' → {len(hits)} matches")
    return hits


def parse_filetype_from_query(query: str):
    """Detect simple file-type filters in a query.

    Returns (exts_set, kinds_set, cleaned_query)
    where exts_set contains lowercase extensions with leading dot (e.g. '.txt').
    """
    q = query.lower()
    exts = set()
    kinds = set()

    mapping = {
        'txt': '.txt',
        'text': '.txt',
        'pdf': '.pdf',
        'docx': '.docx',
        'doc': '.doc',
        'md': '.md',
        'markdown': '.md',
        'image': 'image',
        'images': 'image',
        'jpg': '.jpg',
        'jpeg': '.jpeg',
        'png': '.png',
    }

    tokens = [t for t in q.split() if t]
    remaining = []
    for t in tokens:
        key = t.strip().lower().rstrip('s')
        if key in mapping:
            val = mapping[key]
            if val.startswith('.'):
                exts.add(val)
            else:
                kinds.add(val)
        else:
            remaining.append(t)

    cleaned = ' '.join(remaining).strip()
    return exts, kinds, cleaned


def resolve_file_from_command(command: str) -> Optional[Dict[str, Any]]:
    """
    Given something like 'resume.pdf' or 'C:/Users/.../resume.pdf',
    find the best-matching indexed file.

    We normalise paths to handle Windows '\' vs '/'.
    """
    if not FILE_INDEX:
        return None

    command = command.strip()
    # Normalise separators and case for comparison
    cmd_norm = os.path.normcase(os.path.normpath(command))

    # 1) absolute path match
    for e in FILE_INDEX:
        p_norm = os.path.normcase(os.path.normpath(e["path"]))
        if p_norm == cmd_norm:
            return e

    # Now work with lowercased basename-style command
    cmd_name = os.path.basename(cmd_norm).lower()

    # 2) exact basename match
    exact = [e for e in FILE_INDEX if e["name"] == cmd_name]
    if len(exact) == 1:
        return exact[0]

    # 3) suffix path match (handles partial tail paths)
    suffix_matches = [
        e for e in FILE_INDEX
        if os.path.normcase(os.path.normpath(e["path"])).endswith(cmd_name)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    # 4) startswith filename
    starts = [e for e in FILE_INDEX if e["name"].startswith(cmd_name)]
    if len(starts) == 1:
        return starts[0]

    return None


# -------------------------------------------------------------------
# Helpers: Ollama + PDF summarization
# -------------------------------------------------------------------
def call_ollama(prompt: str, model: Optional[str] = None) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_to_use = model or OLLAMA_MODEL

    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
                "options": {
                    # keep context size reasonable so we don't OOM the model
                    "num_ctx": 2048,
                    "temperature": 0.5,
                },
            },
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
        return f"ERROR: Could not reach Ollama: {e}"

    if resp.status_code != 200:
        # try to parse a nicer error message from Ollama
        try:
            data = resp.json()
            err_msg = data.get("error") or resp.text
        except Exception:
            err_msg = resp.text

        logger.error(f"Ollama error: {err_msg}")

        # Hide ugly 'llama runner process has terminated: exit status 2'
        return f"ERROR: Ollama returned status {resp.status_code}: {err_msg}"

    data = resp.json()
    return data.get("response") or "No response from model."


def summarize_text_file(path: str, ext: str, model: Optional[str] = None) -> str:
    """
    Summarize a generic text-like file (txt, md, rtf, docx) using Ollama.

    We deliberately truncate to a small number of characters so models on
    low-spec machines (4GB VRAM, CPU-only) don’t crash.
    """
    text = extract_text_from_file(path, ext)
    if not text.strip():
        return "I couldn't extract any readable text from this file."

    # Strong truncation to avoid Ollama crashes
    max_chars = 2000
    if len(text) > max_chars:
        text = text[:max_chars]

    prompt = f"""You are a helpful assistant.

Provide a concise summary of this document. Include:
- A short overview (3–5 bullet points)
- Any important dates, names, or numbers
- The main purpose of the document

Document content:
{text}
"""
    summary = call_ollama(prompt, model)

    # If Ollama failed, fall back to returning a text snippet so user still
    # gets useful information instead of a cryptic model crash message.
    if is_ollama_error(summary):
        # include the error text if available
        err_line = ''
        if isinstance(summary, str) and summary.startswith('ERROR:'):
            err_line = summary
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read(4000)
                if not text.strip():
                    return (
                        (err_line + '\n\n') if err_line else ''
                    ) + "I couldn't summarize because the local model failed, and I couldn't extract text from the file."
                # return error then snippet
                prefix = (err_line + '\n\n') if err_line else '(Model unavailable) Extracted text snippet:\n\n'
                return prefix + text
        except Exception:
            return (
                (err_line + '\n\n') if err_line else ''
            ) + (
                "I couldn't summarize because the local model failed, and extracting the file text also failed. Try a smaller model or check file permissions."
            )

    return summary


def summarize_pdf(path: str, model: Optional[str] = None) -> str:
    """Extract text from a PDF and summarize it with Ollama."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return (
            "PDF summarization requires `PyPDF2`. "
            "Please install it with `pip install PyPDF2`."
        )

    try:
        text = ""
        with open(path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages[:10]:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
                if len(text) > 6000:  # keep prompt small
                    break

        if not text.strip():
            return "I couldn't extract any readable text from this PDF."

        prompt = f"""You are a helpful assistant.

Summarize the following PDF for the user. Provide:
- A short overview (3–5 bullet points)
- Any important dates, names, or numbers
- The main purpose of the document

PDF content:
{text}
"""
        summary = call_ollama(prompt, model)

        if is_ollama_error(summary):
            err_line = ''
            if isinstance(summary, str) and summary.startswith('ERROR:'):
                err_line = summary
            try:
                prefix = (err_line + '\n\n') if err_line else '(Model unavailable) Extracted PDF text:\n\n'
                return prefix + text[:8000]
            except Exception:
                return (
                    (err_line + '\n\n') if err_line else ''
                ) + (
                    "I tried to summarize this PDF, but the local model crashed and I couldn't extract the file text. Try a smaller Ollama model."
                )

        return summary
    except Exception as e:
        logger.error(f"PDF summary error for {path}: {e}")
        return f"❌ Failed to process PDF: {e}"

# -------------------------------------------------------------------
# API endpoints
# -------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Local AI Chatbot Backend"}


@app.get("/config")
async def config():
    return {
        "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": OLLAMA_MODEL,
        "embed_model": EMBED_MODEL,
        "file_search_root": FILE_SEARCH_ROOT,
        "version": "3.0.0",
    }


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Main endpoint.

    Behaviors:
    - If query looks like a file path (starts with '/' OR is an absolute path)
      → summarize that file (PDF or text formats).
    - Else:
        * name/folder search on FILE_INDEX
        * vector search on Chroma (content) – but only for longer, natural
          language queries
      If ANY hits → return structured list (no generic AI).
    - Else → fallback to generic AI chat answer.
    """
    query = (request.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(f"Query: {query}")

    # Parse optional file-type filters like 'txt files' or 'pdf'
    exts_filter, kinds_filter, cleaned_query = parse_filetype_from_query(query)

    # --------------------------------------------------------------
    # 1) Direct file command (/file.ext OR absolute path C:\...\file)
    # --------------------------------------------------------------
    command: Optional[str] = None

    # Case 1: user types "/filename.ext"
    if query.startswith("/"):
        command = query[1:].strip()
    # Case 2: UI sends absolute path, e.g. "C:/Users/.../file.docx"
    elif os.path.isabs(query):
        command = query.strip()
    else:
        # Case 3: query exactly equals a known path (safety net)
        q_norm = os.path.normcase(os.path.normpath(query))
        for e in FILE_INDEX:
            if os.path.normcase(os.path.normpath(e["path"])) == q_norm:
                command = query
                break

    if command:
        if not FILE_INDEX:
            return AskResponse(
                answer="No files are indexed yet. Click 'Reindex Files' first.",
                sources=[],
                error="INDEX_EMPTY",
            )

        entry = resolve_file_from_command(command)
        if not entry:
            return AskResponse(
                answer=(
                    f"I couldn't find a unique file matching '{command}' in the index. "
                    "Try reindexing or provide a more specific path or name."
                ),
                sources=[],
                error="FILE_NOT_FOUND",
            )

        ext = entry["extension"].lower()

        if entry["kind"] == "pdf":
            summary = summarize_pdf(entry["path"])
        elif ext in {".txt", ".md", ".rtf", ".docx"}:
            summary = summarize_text_file(entry["path"], ext)
        else:
            summary = (
                f"This is a {entry['kind']} file (extension {ext}). "
                "Automatic summarization is currently implemented for PDFs and common "
                "text formats (.txt, .md, .rtf, .docx)."
            )

        meta_source = {
            "path": entry["path"],
            "name": entry["basename"],
            "directory": entry["directory"],
            "type": entry["kind"],
            "created": entry["created"],
            "modified": entry["modified"],
            "size_bytes": entry["size_bytes"],
        }

        return AskResponse(
            answer=summary,
            sources=[meta_source],
            error=None,
        )

    # --------------------------------------------------------------
    # 2) Name/folder search + (optional) vector search
    #    Respect type filters (e.g., 'txt files') when present
    # --------------------------------------------------------------
    search_query = cleaned_query if cleaned_query else query

    # If there is a strict extension/kind filter and the cleaned query has no
    # meaningful tokens (e.g. user typed 'txt files' or 'pdfs'), return index
    # entries matching only that type. We consider a token meaningful when it is
    # at least 3 characters and not a common stop word.
    name_matches: List[Dict[str, Any]] = []
    def _meaningful_tokens(s: str):
        stop = {'where','what','which','how','are','my','the','a','an','find','show','list','files','file'}
        toks = [t for t in s.split() if len(t) >= 3 and t not in stop]
        return toks

    if (exts_filter or kinds_filter) and len(_meaningful_tokens(cleaned_query)) == 0:
        # collect files matching extension/kind up to max 100
        for entry in FILE_INDEX:
            if exts_filter and entry.get('extension') in exts_filter:
                name_matches.append(entry)
            elif kinds_filter and entry.get('kind') in kinds_filter:
                name_matches.append(entry)
            if len(name_matches) >= 100:
                break
    else:
        name_matches = find_matching_files(search_query, max_results=30)

    # Only use semantic/vector search for "real" questions,
    # not short filename-like queries or when a strict type filter is used
    token_count = len(search_query.split())
    if token_count <= 2 or exts_filter or kinds_filter:
        vec_matches: List[Dict[str, Any]] = []
    else:
        vec_matches = vector_search(search_query, top_k=10)

    # Merge by path
    by_path: Dict[str, Dict[str, Any]] = {}

    for e in name_matches:
        by_path[e["path"]] = {
            "path": e["path"],
            "name": e["basename"],
            "directory": e["directory"],
            "type": e["kind"],
            "created": e["created"],
            "modified": e["modified"],
            "size_bytes": e["size_bytes"],
            "snippet": None,
            "reason": e.get('reason'),
            "reason_detail": e.get('reason_detail','')
        }

    for v in vec_matches:
        existing = by_path.get(v["path"])
        if existing:
            if not existing.get("snippet"):
                existing["snippet"] = v.get("snippet")
        else:
            # Ensure vector hits include reason_detail (use snippet as context)
            by_path[v["path"]] = {
                "path": v.get("path"),
                "name": v.get("name") or os.path.basename(v.get("path","")),
                "directory": v.get("directory"),
                "type": v.get("type") or _file_kind(os.path.splitext(v.get("path",""))[1]),
                "created": v.get("created"),
                "modified": v.get("modified"),
                "size_bytes": v.get("size_bytes"),
                "snippet": v.get("snippet"),
                "reason": v.get("reason","vector"),
                "reason_detail": v.get("snippet") or "vector match"
            }

    hits = list(by_path.values())

    if hits:
        # Apply strict type filters to the final hits if needed
        if exts_filter or kinds_filter:
            filtered = []
            for h in hits:
                ext = os.path.splitext(h.get('path', ''))[1].lower()
                kind = h.get('type') or _file_kind(ext)
                if exts_filter and ext in exts_filter:
                    filtered.append(h)
                elif kinds_filter and kind in kinds_filter:
                    filtered.append(h)
            hits = filtered

        # Build structured, monospaced table (Markdown code block) — remove Type column
        lines: List[str] = []
        header = "Idx  Size(KB)  Created              Modified             Name"
        sep = "-" * len(header)
        lines.append(header)
        lines.append(sep)

        for i, h in enumerate(hits, start=1):
            size_kb = (h.get("size_bytes") or 0) / 1024.0
            created = (h.get("created") or "")[:19]
            modified = (h.get("modified") or "")[:19]
            name = h.get("name") or h.get("basename") or os.path.basename(h.get('path', ''))

            line = (
                f"{str(i).rjust(3)}  {size_kb:8.1f}  "
                f"{created:19}  {modified:19}  {name}"
            )
            lines.append(line)

        listing = "\n".join(lines)

        answer = f"I found {len(hits)} matching file(s). See the table below."

        md = "```text\n" + listing + "\n```"

        return AskResponse(answer=answer, sources=hits, error=None, markdown=md)

    # --------------------------------------------------------------
    # 3) Fallback → generic AI answer (no local files matched)
    # --------------------------------------------------------------
    prompt = (
        "You are a helpful assistant running locally. "
        "No local files matched the user's keywords. "
        "Answer the user's question based only on your general knowledge.\n\n"
        f"User: {query}"
    )
    answer = call_ollama(prompt, request.model)
    return AskResponse(answer=answer, sources=[], error=None)


@app.post("/reindex")
async def reindex():
    """
    Rebuild FILE_INDEX (metadata) and Chroma vector store (content).
    """
    global FILE_INDEX

    # 1) File metadata index
    FILE_INDEX = build_file_index(FILE_SEARCH_ROOT)

    # If nothing was found in the configured root, attempt common user folders
    if not FILE_INDEX:
        logger.info("No files found under FILE_SEARCH_ROOT; attempting common user folders...")
        home = os.path.expanduser('~')
        fallbacks = [os.path.join(home, 'Documents'), os.path.join(home, 'Desktop'), os.path.join(home, 'Downloads')]
        for fb in fallbacks:
            if os.path.exists(fb):
                logger.info(f"Trying fallback folder: {fb}")
                extra = build_file_index(fb)
                if extra:
                    # merge unique paths
                    existing_paths = {e['path'] for e in FILE_INDEX}
                    for e in extra:
                        if e['path'] not in existing_paths:
                            FILE_INDEX.append(e)
                    if FILE_INDEX:
                        break

    # 2) Clear Chroma by recreating collection (skip if chroma disabled)
    global collection
    if chroma_client is None:
        logger.info("Chroma client not available; skipping vector reindex")
        collection = None
    else:
        try:
            chroma_client.delete_collection("local_docs")
        except Exception:
            pass  # ok if it doesn't exist yet
        collection = chroma_client.get_or_create_collection("local_docs")

    docs: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for entry in FILE_INDEX:
        path = entry["path"]
        ext = entry["extension"]
        text = extract_text_from_file(path, ext)
        if not text:
            continue

        chunks = split_into_chunks(text)
        if not chunks:
            continue

        for i, chunk in enumerate(chunks):
            docs.append(chunk)
            metadatas.append(
                {
                    "path": path,
                    "filename": entry["basename"],
                    "directory": entry["directory"],
                    "created": entry["created"],
                    "modified": entry["modified"],
                    "size_bytes": entry["size_bytes"],
                    "chunk_index": i,
                }
            )
            ids.append(f"{path}__chunk_{i}")

    if docs and collection is not None:
        try:
            logger.info(f"Embedding {len(docs)} chunks for Chroma...")
            embeddings = embed_text(docs)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=docs,
                metadatas=metadatas,
            )
            logger.info("Chroma index updated.")
        except Exception as e:
            logger.error(f"Error adding to Chroma: {e}")
    elif docs:
        logger.info("Chroma collection not available, skipping adding embeddings")

    return {
        "status": "ok",
        "file_search_root": FILE_SEARCH_ROOT,

        # our fields
        "files_indexed": len(FILE_INDEX),
        "chunks_indexed": len(docs),

        # extra aliases for the frontend
        "files": len(FILE_INDEX),
        "chunks": len(docs),
        "count": len(FILE_INDEX),
        "sample_files": [f["path"] for f in FILE_INDEX[:6]],
    }


@app.post('/search')
async def api_search(req: SearchRequest):
    """Search API: returns JSON list of matches and a markdown table for UI rendering."""
    query = (req.query or '').strip()
    if not query:
        raise HTTPException(status_code=400, detail='Query cannot be empty')

    exts_filter, kinds_filter, cleaned_query = parse_filetype_from_query(query)
    search_query = cleaned_query if cleaned_query else query

    # simple name search
    if (exts_filter or kinds_filter) and not cleaned_query:
        # return files of that type
        matches = []
        for e in FILE_INDEX:
            if (exts_filter and e.get('extension') in exts_filter) or (kinds_filter and e.get('kind') in kinds_filter):
                ee = dict(e)
                ee['reason'] = 'type'
                matches.append(ee)
    else:
        matches = find_matching_files(search_query, max_results=200)

    # Build structured results
    results = []
    for e in matches:
        results.append({
            'path': e['path'],
            'name': e['basename'],
            'directory': e['directory'],
            'type': e['kind'],
            'created': e['created'],
            'modified': e['modified'],
            'size_bytes': e['size_bytes'],
            'reason': e.get('reason'),
            'reason_detail': e.get('reason_detail',''),
            'open_url': f"file:///{e['path'].replace('\\','/')}"
        })

    # markdown table
    header = "Idx  Size(KB)  Created              Modified             Name"
    sep = "-" * len(header)
    lines = [header, sep]
    for i, r in enumerate(results, start=1):
        size_kb = (r.get('size_bytes') or 0) / 1024.0
        created = (r.get('created') or '')[:19]
        modified = (r.get('modified') or '')[:19]
        name = r.get('name')
        lines.append(f"{str(i).rjust(3)}  {size_kb:8.1f}  {created:19}  {modified:19}  {name}")

    md = "```text\n" + "\n".join(lines) + "\n```"

    return {'count': len(results), 'results': results, 'markdown': md}


@app.post('/file_info')
async def api_file_info(req: FileRequest):
    path = req.path
    norm = os.path.normcase(os.path.normpath(path))
    for e in FILE_INDEX:
        if os.path.normcase(os.path.normpath(e['path'])) == norm:
            return {
                'path': e['path'],
                'name': e['basename'],
                'directory': e['directory'],
                'type': e['kind'],
                'created': e['created'],
                'modified': e['modified'],
                'size_bytes': e['size_bytes'],
                'open_url': f"file:///{e['path'].replace('\\','/')}"
            }
    raise HTTPException(status_code=404, detail='File not found in index')


@app.post('/analyze_file')
async def api_analyze_file(req: FileRequest):
    path = req.path
    norm = os.path.normcase(os.path.normpath(path))
    entry = None
    for e in FILE_INDEX:
        if os.path.normcase(os.path.normpath(e['path'])) == norm:
            entry = e
            break
    if not entry:
        raise HTTPException(status_code=404, detail='File not found in index')

    ext = entry['extension'].lower()
    result = {'metadata': entry}
    if entry['kind'] == 'pdf':
        result['summary'] = summarize_pdf(entry['path'], req.model)
    elif ext in {'.txt', '.md', '.rtf', '.docx'}:
        result['summary'] = summarize_text_file(entry['path'], ext, req.model)
    else:
        result['summary'] = f"No automatic summary available for type {entry['kind']}"

    return result


@app.get("/list-all-files")
async def list_all_files():
    """
    Return all indexed files in a readable format.
    """
    files = []
    for entry in FILE_INDEX:
        files.append({
            "path": entry["path"],
            "name": entry["basename"],
            "directory": entry["directory"],
            "type": entry["kind"],
            "created": entry["created"],
            "modified": entry["modified"],
            "size_bytes": entry["size_bytes"],
        })
    return {"count": len(files), "files": files}


@app.get("/stats")
async def stats():
    return {
        "status": "ok",
        "files_indexed": len(FILE_INDEX),
        "file_search_root": FILE_SEARCH_ROOT,
    }


@app.post('/open_file')
async def open_file(req: FileRequest):
    """Open a file on the host OS (Windows). Only opens files present in the index.

    This is a convenience used by the UI when a user clicks a file. We ensure the
    file exists in `FILE_INDEX` to reduce risk of arbitrary file execution.
    """
    path = req.path
    # Normalize and ensure indexed
    norm = os.path.normcase(os.path.normpath(path))
    allowed = False
    for e in FILE_INDEX:
        if os.path.normcase(os.path.normpath(e['path'])) == norm:
            allowed = True
            break

    if not allowed:
        raise HTTPException(status_code=403, detail='File not permitted to open')

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='File not found')

    try:
        # Windows: os.startfile; on other OS you could use subprocess
        os.startfile(path)
        return {'status': 'ok', 'message': 'File opened'}
    except Exception as e:
        logger.error(f'open_file error for {path}: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/file_stream')
async def file_stream(path: str = Query(..., description='Absolute path to indexed file')):
    """Stream an indexed file (used for preview in the UI). Only serves files present in the index."""
    norm = os.path.normcase(os.path.normpath(path))
    allowed = False
    for e in FILE_INDEX:
        if os.path.normcase(os.path.normpath(e['path'])) == norm:
            allowed = True
            break

    if not allowed:
        raise HTTPException(status_code=403, detail='File not permitted')

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='File not found')

    # Use FileResponse to let the browser display PDFs natively
    return FileResponse(path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)
